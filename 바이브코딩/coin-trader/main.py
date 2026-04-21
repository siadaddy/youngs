#!/usr/bin/env python3
"""
🤖 AI 코인 자동매매 시스템
━━━━━━━━━━━━━━━━━━━━━━━━━━━
흐름: 분석 → AI 판단 → 손절 체크 → 주문 실행 → 알림
4시간마다 launchd로 자동 실행
"""

import sys, os, json, time, requests, subprocess, signal
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from dotenv import load_dotenv
from agents import analyzer, ai_advisor, executor

load_dotenv()

STATE_FILE    = os.path.join(os.path.dirname(__file__), "state.json")
LOG_FILE      = os.path.join(os.path.dirname(__file__), "trader.log")
IP_FILE       = os.path.join(os.path.dirname(__file__), "ip.txt")
FAILURE_FILE  = os.path.join(os.path.dirname(__file__), "failure_state.json")
LOCK_FILE     = os.path.join(os.path.dirname(__file__), "main.lock")
NTFY_TOPIC   = os.getenv("NTFY_TOPIC", "siadad-aicrew")
STOP_LOSS          = float(os.getenv("STOP_LOSS_PCT", "4.0"))
TAKE_PROFIT        = float(os.getenv("TAKE_PROFIT_PCT", "5.0"))
TRAILING_STOP_PCT  = float(os.getenv("TRAILING_STOP_PCT", "2.5"))
TRAILING_ACTIVATE  = float(os.getenv("TRAILING_ACTIVATE_PCT", "3.0"))
MAX_HOLD_HOURS     = float(os.getenv("MAX_HOLD_HOURS", "8.0"))
DRY_RUN            = os.getenv("DRY_RUN", "true").lower() == "true"
DAILY_LOSS_LIMIT   = float(os.getenv("DAILY_LOSS_LIMIT_KRW", "-7500"))  # 5만원 기준 일일 손실 한도
SWITCH_COOLDOWN_HOURS = 2  # 기회 교체 후 해당 종목 재진입 금지 시간


# ── 유틸리티 ─────────────────────────────────────────────

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)  # plist StandardOutPath가 trader.log로 redirect — 파일 중복 쓰기 방지


def notify(title: str, message: str, priority: str = "default"):
    priority_map = {"default": 3, "high": 4, "urgent": 5}
    try:
        requests.post(
            "https://ntfy.sh/",
            json={
                "topic":    NTFY_TOPIC,
                "title":    title,
                "message":  message,
                "priority": priority_map.get(priority, 3),
                "tags":     ["coin", "robot"],
            },
            timeout=5,
        )
    except Exception:
        pass


def load_state() -> dict | None:
    """state.json에서 보유 상태 로드"""
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data.get("ticker") else None
    except Exception:
        return None


def save_state(holding: dict | None):
    """보유 상태 저장"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(holding or {}, f, ensure_ascii=False, indent=2)


def _cleanup_orphaned_holdings(holding: dict | None):
    """state.json에 없는 잔여 코인 감지 → 자동 매도 (BIOT 같은 사례 방지)"""
    from utils.bithumb_client import get_coin_balance, get_current_price, sell_market_order

    current_ticker = holding["ticker"] if holding else None

    # trades.json 히스토리에서 최근 BUY 종목 목록 수집
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.path.dirname(__file__), text=True
        ).strip()
        trades_path = os.path.join(repo_root, "docs", "trades.json")
        with open(trades_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    # 현재 holding이 아닌 BUY 기록 종목만 추출 (중복 제거)
    candidates = {
        e["ticker"] for e in data.get("history", [])
        if e.get("action") == "BUY" and e.get("ticker") and e.get("ticker") != current_ticker
    }

    if not candidates:
        return

    for ticker in candidates:
        try:
            qty = get_coin_balance(ticker)
            if qty <= 0:
                continue
            price = get_current_price(ticker)
            if price <= 0:
                log(f"  ⚠️  [orphan] {ticker}: 현재가 조회 실패 — 스킵")
                continue
            value = qty * price
            if value < 5000:
                log(f"  ℹ️  [orphan] {ticker}: {qty:.4f}개 ({value:.0f}원) — 최소금액 미달, 스킵")
                continue
            log(f"  🧹 [orphan] {ticker} {qty:.4f}개 ({value:,.0f}원) 잔여 감지 → 즉시 매도")
            sell_market_order(ticker, qty)
            notify(
                "🧹 잔여 코인 자동 정리",
                f"{ticker} {qty:.4f}개 ({value:,.0f}원)\nstate.json 미등록 잔여 코인 자동 매도 완료",
                priority="high",
            )
            log(f"  ✅ [orphan] {ticker} 매도 완료")
        except Exception as e:
            log(f"  ⚠️  [orphan] {ticker} 처리 실패 (무시): {e}")


# ── 손절 후 재진입 쿨다운 ─────────────────────────────────
COOLDOWN_FILE  = os.path.join(os.path.dirname(__file__), "cooldown.json")
COOLDOWN_HOURS = 6   # 손절 후 같은 종목 재진입 금지 시간 (3→6시간)
GLOBAL_COOLDOWN_HOURS = 4  # 손절 후 모든 종목 매수 금지 시간 (2→4시간)

def get_cooldown_tickers() -> list:
    """현재 쿨다운 중인 종목 목록 반환 (_global 제외)"""
    if not os.path.exists(COOLDOWN_FILE):
        return []
    try:
        with open(COOLDOWN_FILE, "r") as f:
            data = json.load(f)
        now = datetime.now()
        active = []
        expired = []
        for ticker, until_str in data.items():
            if ticker == "_global":
                continue
            until = datetime.strptime(until_str, "%Y-%m-%d %H:%M")
            if now < until:
                active.append(ticker)
                log(f"  ⛔ 쿨다운 중: {ticker} (해제: {until_str})")
            else:
                expired.append(ticker)
        # 만료된 쿨다운 정리
        if expired:
            for t in expired:
                del data[t]
            with open(COOLDOWN_FILE, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return active
    except Exception:
        return []

def is_global_cooldown() -> bool:
    """전역 쿨다운 중이면 True (손절 후 모든 종목 매수 금지)"""
    if not os.path.exists(COOLDOWN_FILE):
        return False
    try:
        with open(COOLDOWN_FILE, "r") as f:
            data = json.load(f)
        until_str = data.get("_global")
        if not until_str:
            return False
        until = datetime.strptime(until_str, "%Y-%m-%d %H:%M")
        if datetime.now() < until:
            log(f"  🚫 전역 매수 쿨다운 중 (해제: {until_str}) — 모든 BUY 금지")
            return True
        # 만료 → 삭제
        del data["_global"]
        with open(COOLDOWN_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return False
    except Exception:
        return False

def add_cooldown(ticker: str):
    """손절 후 종목 쿨다운 + 전역 쿨다운 동시 등록"""
    try:
        data = {}
        if os.path.exists(COOLDOWN_FILE):
            with open(COOLDOWN_FILE, "r") as f:
                data = json.load(f)
        from datetime import timedelta
        now = datetime.now()
        ticker_until = (now + timedelta(hours=COOLDOWN_HOURS)).strftime("%Y-%m-%d %H:%M")
        global_until = (now + timedelta(hours=GLOBAL_COOLDOWN_HOURS)).strftime("%Y-%m-%d %H:%M")
        data[ticker]   = ticker_until
        data["_global"] = global_until
        with open(COOLDOWN_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"  ⛔ 종목 쿨다운: {ticker} → {ticker_until}까지")
        log(f"  🚫 전역 쿨다운: 모든 BUY → {global_until}까지 금지")
    except Exception as e:
        log(f"  ⚠️  쿨다운 등록 실패 (무시): {e}")


def _add_switch_cooldown(ticker: str):
    """기회 교체 SELL 후 해당 종목 단기 쿨다운 등록 (전역 쿨다운 없음)
    손절보다 짧게 — 같은 종목 즉시 재매수만 차단"""
    try:
        data = {}
        if os.path.exists(COOLDOWN_FILE):
            with open(COOLDOWN_FILE, "r") as f:
                data = json.load(f)
        from datetime import timedelta
        until = (datetime.now() + timedelta(hours=SWITCH_COOLDOWN_HOURS)).strftime("%Y-%m-%d %H:%M")
        # 이미 더 긴 쿨다운이 있으면 덮어쓰지 않음
        existing = data.get(ticker)
        if existing and datetime.strptime(existing, "%Y-%m-%d %H:%M") > datetime.strptime(until, "%Y-%m-%d %H:%M"):
            return
        data[ticker] = until
        with open(COOLDOWN_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"  🔄 교체 쿨다운: {ticker} → {until}까지 재진입 금지 ({SWITCH_COOLDOWN_HOURS}시간)")
    except Exception as e:
        log(f"  ⚠️  교체 쿨다운 등록 실패 (무시): {e}")


# ── Daily Drawdown ────────────────────────────────────────
DRAWDOWN_FILE = os.path.join(os.path.dirname(__file__), "drawdown.json")

def load_drawdown() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(DRAWDOWN_FILE):
        try:
            with open(DRAWDOWN_FILE, "r") as f:
                d = json.load(f)
            if d.get("date") == today:
                return d
        except Exception:
            pass
    return {"date": today, "daily_loss_krw": 0.0, "paused": False}

def save_drawdown(d: dict):
    with open(DRAWDOWN_FILE, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def check_drawdown_limit() -> bool:
    """일일 손실 한도 초과 여부 반환 (True = 초과, 봇 정지)"""
    d = load_drawdown()
    if d["paused"]:
        log(f"  🛑 Daily limit reached — 오늘 손실 {d['daily_loss_krw']:,.0f}원 / 한도 {DAILY_LOSS_LIMIT:,.0f}원 — bot paused")
        return True
    return False

def record_loss(pnl_krw: float):
    """손실 발생 시 drawdown 누적 기록"""
    if pnl_krw >= 0:
        return
    d = load_drawdown()
    d["daily_loss_krw"] += pnl_krw
    if d["daily_loss_krw"] <= DAILY_LOSS_LIMIT:
        d["paused"] = True
        log(f"  🛑 Daily Drawdown Limit reached! 누적 손실 {d['daily_loss_krw']:,.0f}원 — bot paused")
        notify("🛑 일일 손실 한도 도달", f"오늘 누적 손실: {d['daily_loss_krw']:,.0f}원\n한도: {DAILY_LOSS_LIMIT:,.0f}원\n봇이 오늘 하루 정지됩니다.", priority="urgent")
    save_drawdown(d)


def retry(label: str, fn, *args, **kwargs):
    for attempt in range(1, 4):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if attempt < 3:
                log(f"  ⚠️  [{label}] 실패 ({attempt}/3): {e} — 10초 후 재시도")
                time.sleep(10)
            else:
                log(f"  ❌ [{label}] 3회 모두 실패: {e}")
                raise


# ── IP 변경 감지 ──────────────────────────────────────────

def record_failure(reason: str):
    """실패 사이클 기록 — 다음 성공 사이클에서 ntfy 알림"""
    try:
        data = {"failed_cycles": 1, "last_failure": datetime.now().strftime("%Y-%m-%d %H:%M"), "reason": reason}
        if os.path.exists(FAILURE_FILE):
            with open(FAILURE_FILE, "r") as f:
                prev = json.load(f)
            data["failed_cycles"] = prev.get("failed_cycles", 0) + 1
        with open(FAILURE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def check_and_notify_failures():
    """이전 실패 사이클이 있으면 ntfy 발송 후 초기화"""
    if not os.path.exists(FAILURE_FILE):
        return
    try:
        with open(FAILURE_FILE, "r") as f:
            data = json.load(f)
        n = data.get("failed_cycles", 0)
        if n > 0:
            notify(
                f"⚠️ 자동매매 복구 ({n}회 실패 후)",
                f"이전 {n}개 사이클 실패\n마지막 실패: {data.get('last_failure','?')}\n원인: {data.get('reason','?')}\n\n현재 정상 재개됨",
                priority="high",
            )
            log(f"  ⚠️  이전 {n}회 실패 감지 — ntfy 복구 알림 발송")
        os.remove(FAILURE_FILE)
    except Exception:
        pass


def check_ip_change():
    """현재 공인 IP 확인 → 이전과 다르면 ntfy 알림"""
    try:
        current_ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        log("  ⚠️  IP 확인 실패 (무시)")
        return

    prev_ip = None
    if os.path.exists(IP_FILE):
        with open(IP_FILE, "r") as f:
            prev_ip = f.read().strip()

    with open(IP_FILE, "w") as f:
        f.write(current_ip)

    if prev_ip and prev_ip != current_ip:
        log(f"  🔴 IP 변경 감지: {prev_ip} → {current_ip}")
        notify(
            "🔴 IP 변경 감지 — API 키 재등록 필요",
            f"공인 IP가 변경됐습니다!\n이전: {prev_ip}\n현재: {current_ip}\n\n빗썸 API 키 IP 허용 목록을 업데이트하세요.",
            priority="urgent",
        )
    else:
        log(f"  🌐 IP 정상: {current_ip} (변경 없음 — 알림 스킵)")


# ── 손절 / 익절 체크 ──────────────────────────────────────

def update_high_price(holding: dict) -> dict:
    """현재가가 고점보다 높으면 high_price 갱신 후 state 저장"""
    from utils.bithumb_client import get_current_price
    try:
        now = get_current_price(holding["ticker"])
        if now and now > holding.get("high_price", holding["buy_price"]):
            holding["high_price"] = now
            save_state(holding)
            log(f"  📈 고점 갱신: {holding['ticker']} → {now:,.0f}원")
    except Exception:
        pass
    return holding


def check_exit(holding: dict) -> str | None:
    """손절/익절/트레일링스탑/시간초과 확인
    반환: 'stop_loss' | 'take_profit' | 'trailing_stop' | 'time_exit' | None
    """
    from utils.bithumb_client import get_current_price
    now = get_current_price(holding["ticker"])
    if not now or not holding.get("buy_price"):
        return None

    pct = (now / holding["buy_price"] - 1) * 100

    # ── 1. 일반 손절 ──────────────────────────────────────
    if pct <= -STOP_LOSS:
        log(f"  🔴 손절 발동: {holding['ticker']} | {pct:.2f}% (기준: -{STOP_LOSS}%)")
        return "stop_loss"

    # ── 2. 일반 익절 ──────────────────────────────────────
    if pct >= TAKE_PROFIT:
        log(f"  🟡 익절 발동: {holding['ticker']} | {pct:.2f}% (기준: +{TAKE_PROFIT}%)")
        return "take_profit"

    # ── 3. 트레일링 스탑 (+3% 이상 수익 구간에서 활성) ────
    high = holding.get("high_price", holding["buy_price"])
    high_pct = (high / holding["buy_price"] - 1) * 100
    if high_pct >= TRAILING_ACTIVATE:
        trail_pct = (now / high - 1) * 100
        if trail_pct <= -TRAILING_STOP_PCT:
            log(f"  🟠 트레일링 스탑: {holding['ticker']} | 고점 대비 {trail_pct:.2f}% 하락 (고점 {high:,.0f}원 → 현재 {now:,.0f}원)")
            return "trailing_stop"

    # ── 4. 시간 기반 강제 청산 (죽은 포지션 정리) ─────────
    if holding.get("buy_time"):
        try:
            buy_dt = datetime.strptime(holding["buy_time"], "%Y-%m-%d %H:%M")
            hold_hours = (datetime.now() - buy_dt).total_seconds() / 3600
            if hold_hours >= MAX_HOLD_HOURS and pct <= -1.0:
                log(f"  ⏰ 시간 초과 강제 청산: {holding['ticker']} | {hold_hours:.1f}시간 보유 | 수익률 {pct:.2f}%")
                return "time_exit"
        except Exception:
            pass

    return None


# ── 메인 ─────────────────────────────────────────────────

class _TraderTimeout(BaseException):
    """SIGALRM 하드 타임아웃 — except Exception 에 잡히지 않음"""
    pass


def _timeout_handler(signum, frame):
    raise _TraderTimeout("전체 실행 10분 초과 — 강제 종료")


def main():
    # 전체 실행 타임아웃 10분 (네트워크 hang 방지)
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(600)

    # price_monitor.py 와의 충돌 방지용 lock 파일 생성
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    dry_tag = " [DRY RUN]" if DRY_RUN else ""
    log(f"\n{'='*55}")
    log(f"🤖 AI 코인 자동매매 시작 — {now_str}{dry_tag}")
    log(f"{'='*55}")

    # Step 0: 이전 실패 체크 + IP 변경 감지
    check_and_notify_failures()
    check_ip_change()

    # Step 0-1: 일일 손실 한도 체크
    if check_drawdown_limit():
        return

    # Step 1: 보유 상태 로드
    holding = load_state()

    # Step 1-1: orphaned 포지션 감지 및 정리
    # state.json에 없지만 빗썸에 실제 잔고가 남아있는 코인 자동 매도
    _cleanup_orphaned_holdings(holding)
    if holding:
        hold_hours = ""
        if holding.get("buy_time"):
            try:
                buy_dt = datetime.strptime(holding["buy_time"], "%Y-%m-%d %H:%M")
                elapsed = (datetime.now() - buy_dt).total_seconds() / 3600
                hold_hours = f" | 보유 {elapsed:.1f}시간"
            except Exception:
                pass
        bp = holding['buy_price']
        bp_str = f"{bp:,.0f}원" if bp >= 1 else f"{bp:.4f}원"
        log(f"  📦 현재 보유: {holding['ticker']} | 매수가 {bp_str} | {holding['qty']:.8f}개{hold_hours}")
    else:
        log("  📦 현재 보유 종목 없음")

    # Step 2: 고점 갱신 + 손절/익절/트레일링/시간초과 체크
    if holding:
        holding = update_high_price(holding)  # 고점 추적 갱신

        try:
            exit_type = check_exit(holding)
        except Exception as e:
            log(f"  ⚠️  손절/익절 체크 실패 (무시하고 계속): {e}")
            exit_type = None

        exit_labels = {
            "stop_loss":     ("🔴 손절 매도",     f"자동 손절 -{STOP_LOSS}%",       "high"),
            "take_profit":   ("🟡 익절 매도",     f"자동 익절 +{TAKE_PROFIT}%",     "high"),
            "trailing_stop": ("🟠 트레일링 익절", f"트레일링 스탑 (고점 대비 -{TRAILING_STOP_PCT}%)", "high"),
            "time_exit":     ("⏰ 시간 초과 청산", f"{MAX_HOLD_HOURS:.0f}시간 보유 + 수익률 -1% 미만", "default"),
        }

        if exit_type in exit_labels:
            notif_title, sell_reason, priority = exit_labels[exit_type]
            action = {"action": "SELL", "ticker": holding["ticker"], "reason": sell_reason}
            try:
                new_holding = executor.run(action, holding)
                save_state(new_holding)
                notify(notif_title, f"{action['ticker']} 매도 완료\n이유: {sell_reason}", priority=priority)
                _publish_trades("SELL", action, new_holding, holding)
                if exit_type == "stop_loss":
                    pnl = -(holding.get("invest_krw", 0) * STOP_LOSS / 100)
                    record_loss(pnl)
                    add_cooldown(holding["ticker"])
                holding = None
                log(f"  {exit_type} 처리 완료 — 즉시 매수 기회 탐색 계속")
            except Exception as e:
                log(f"  ❌ {exit_type} 매도 실패: {e}")
                notify(f"❌ {exit_type} 실패", f"{holding['ticker']} 매도 오류: {e}", priority="urgent")
                return

    # Step 3: 시장 분석
    try:
        market_data = retry("시장 분석", analyzer.run)
    except Exception as e:
        is_network = "NameResolution" in str(e) or "Failed to resolve" in str(e) or "timed out" in str(e).lower()
        record_failure("네트워크 실패" if is_network else f"시장분석 실패: {e}")
        notify("❌ 자동매매 오류", f"시장 분석 실패: {e}", priority="high")
        return

    # Step 3-1: 쿨다운 종목 목록 조회
    cooldown_tickers = get_cooldown_tickers()

    # Step 4: AI 판단
    try:
        advice = retry("AI 판단", ai_advisor.run, market_data, holding, cooldown_tickers)
    except Exception as e:
        record_failure(f"AI판단 실패: {e}")
        notify("❌ 자동매매 오류", f"AI 판단 실패: {e}", priority="high")
        return

    # Step 4-1: AI 손절 오판 차단 — 실제 수익률이 양수인데 손절로 SELL 지시한 경우
    if advice["action"] == "SELL" and holding:
        from utils.bithumb_client import get_current_price
        _now = get_current_price(holding["ticker"])
        if _now and holding.get("buy_price"):
            _actual_pct = (_now / holding["buy_price"] - 1) * 100
            if _actual_pct > -STOP_LOSS:
                _reason = advice.get("reason", "")
                if any(kw in _reason for kw in ["손절", "이하", "-7", "-5", "-%"]):
                    log(f"  ⚠️  AI 손절 오판 차단 — 실제 수익률 {_actual_pct:+.2f}% → HOLD 유지")
                    advice = {"action": "HOLD", "ticker": holding["ticker"], "reason": f"AI 손절 오판 차단 (실제 {_actual_pct:+.2f}%)"}

    # Step 5: BUY 시 전역 쿨다운 체크 (손절 후 모든 종목 매수 금지)
    if advice["action"] == "BUY" and holding is None:
        if is_global_cooldown():
            advice = {"action": "HOLD", "ticker": None, "reason": "손절 후 전역 쿨다운 중 — BUY 차단"}
            log("  🚫 전역 쿨다운으로 BUY 차단 → HOLD")

    # Step 6: 주문 실행
    try:
        new_holding = executor.run(advice, holding)
    except Exception as e:
        log(f"  ❌ 주문 실행 실패: {e}")
        notify("❌ 자동매매 오류", f"주문 실행 실패: {e}", priority="high")
        return

    # Step 6-1: SELL 완료 직후 즉시 매수 기회 재탐색 (전역 쿨다운 없을 때만)
    if advice["action"] == "SELL" and new_holding is None:
        save_state(None)
        _publish_trades("SELL", advice, None, holding)
        notify("🔴 매도 완료", f"{advice.get('ticker')} 매도\n이유: {advice.get('reason','')}")

        # ★ 기회 교체 SELL 시 해당 종목에 단기 쿨다운 등록 (즉시 재매수 방지)
        if holding:
            sold_ticker = holding["ticker"]
            reason_text = advice.get("reason", "")
            if "기회 교체" in reason_text or advice.get("action") == "SELL":
                _add_switch_cooldown(sold_ticker)

        if is_global_cooldown():
            log("  🚫 전역 쿨다운 중 — 즉시 매수 재판단 스킵")
            return
        log("  🔄 매도 완료 → 즉시 매수 기회 재판단 (시장 데이터 재수집)...")
        holding = None

        # ★ 시장 데이터 재수집 — 같은 데이터로 재판단하면 똑같은 결론
        try:
            fresh_market_data = retry("시장 재분석", analyzer.run)
        except Exception as e:
            log(f"  ⚠️  시장 재분석 실패: {e}")
            return

        try:
            fresh_cooldowns = get_cooldown_tickers()  # 방금 등록한 쿨다운 반영
            buy_advice = retry("AI 매수 재판단", ai_advisor.run, fresh_market_data, None, fresh_cooldowns)
        except Exception as e:
            log(f"  ⚠️  매수 재판단 실패: {e}")
            return
        if buy_advice["action"] == "BUY":
            try:
                new_holding = executor.run(buy_advice, None)
                save_state(new_holding)
                price = new_holding["buy_price"] if new_holding else 0
                notify("🟢 즉시 매수 완료", f"{buy_advice.get('ticker')} 매수\n단가: {price:,.0f}원\n이유: {buy_advice.get('reason','')}")
                _publish_trades("BUY", buy_advice, new_holding, None)
                log(f"  ✅ 즉시 매수 완료: {buy_advice.get('ticker')}")
            except Exception as e:
                log(f"  ❌ 즉시 매수 실패: {e}")
        else:
            log("  ℹ️  즉시 매수 신호 없음 — HOLD 유지")
        return  # SELL+재판단 완료, 이하 중복 처리 스킵

    # Step 6: 상태 저장
    save_state(new_holding)

    # Step 7: 결과 알림
    action  = advice["action"]
    reason  = advice.get("reason", "")
    ticker  = advice.get("ticker") or (new_holding["ticker"] if new_holding else "-")

    if action == "BUY":
        price = new_holding["buy_price"] if new_holding else 0
        notify(
            f"🟢 매수 완료 {dry_tag}",
            f"{ticker} 매수\n단가: {price:,.0f}원\n이유: {reason}",
        )
    elif action == "SELL" and new_holding is None:
        # executor가 실제로 매도한 경우만 알림
        notify(
            f"🔴 매도 완료 {dry_tag}",
            f"{ticker} 매도\n이유: {reason}",
        )
    # HOLD는 매시간 알림 불필요 — 알림 없음

    # executor가 실제로 실행했는지 여부로 로그 구분
    if action == "SELL" and new_holding is not None:
        log(f"⏸  SELL 차단 — 최소금액 미달, HOLD 유지 ({ticker})")
    elif action == "BUY" and new_holding is None:
        log(f"⚠️  BUY 지시 but 매수 미체결 (잔고 부족?)")
    else:
        log(f"✅ 완료 — {action} {ticker}")
    signal.alarm(0)  # 타임아웃 해제

    # Step 8: GitHub Pages용 trades.json 업데이트 & push
    _publish_trades(action, advice, new_holding, holding)


def _publish_trades(action: str, advice: dict, new_holding: dict | None, old_holding: dict | None):
    """매매 결과를 docs/trades.json에 저장하고 GitHub에 push"""
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.path.dirname(__file__), text=True
        ).strip()
        trades_path = os.path.join(repo_root, "docs", "trades.json")

        # 기존 데이터 로드
        if os.path.exists(trades_path):
            with open(trades_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"holding": None, "history": [], "stats": {
                "total_trades": 0, "wins": 0, "losses": 0,
                "total_pnl_krw": 0, "start_date": datetime.now().strftime("%Y-%m-%d"),
                "stop_loss_pct": STOP_LOSS, "take_profit_pct": TAKE_PROFIT
            }}

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 히스토리 추가 (실제 체결된 경우만)
        # SELL: new_holding is None = 실제 매도 완료 / BUY: new_holding 존재 = 실제 매수 완료
        if (action == "SELL" and new_holding is None) or (action == "BUY" and new_holding):
            from utils.bithumb_client import get_current_price
            ticker = advice.get("ticker") or (old_holding["ticker"] if old_holding else "-")
            price  = get_current_price(ticker) if ticker != "-" else 0
            pnl_pct = None
            pnl_krw = None
            if action == "SELL" and old_holding and old_holding.get("buy_price"):
                pnl_pct = round((price / old_holding["buy_price"] - 1) * 100, 2)
                pnl_krw = round((price - old_holding["buy_price"]) * old_holding.get("qty", 0), 0)
                data["stats"]["total_trades"] += 1
                if pnl_pct >= 0:
                    data["stats"]["wins"] += 1
                else:
                    data["stats"]["losses"] += 1
                data["stats"]["total_pnl_krw"] = round(
                    data["stats"].get("total_pnl_krw", 0) + (pnl_krw or 0), 0
                )
            entry = {
                "time": now_str,
                "action": action,
                "ticker": ticker,
                "price": price,
                "amount_krw": new_holding.get("invest_krw") if new_holding else old_holding.get("invest_krw", 0),
                "reason": advice.get("reason", ""),
                "pnl_pct": pnl_pct,
                "pnl_krw": pnl_krw,
                "dry_run": DRY_RUN,
            }
            data["history"].insert(0, entry)
            data["history"] = data["history"][:50]  # 최근 50건만 보관

        # 현재 보유 상태 업데이트
        data["holding"] = new_holding
        data["updated_at"] = now_str

        with open(trades_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # git push: 실제 체결된 경우(BUY 성공 or SELL 성공)만 커밋/푸시
        actually_executed = (action == "BUY" and new_holding) or (action == "SELL" and new_holding is None)
        ticker_str = advice.get("ticker") or (new_holding["ticker"] if new_holding else "")
        dry_str = " [DRY]" if DRY_RUN else ""
        subprocess.run(["git", "add", "docs/trades.json"], cwd=repo_root, check=True)
        if actually_executed:
            subprocess.run(
                ["git", "commit", "-m", f"trade: {now_str} {action} {ticker_str}{dry_str}"],
                cwd=repo_root, check=True
            )
            subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
            log("  ✅ trades.json GitHub 업데이트 완료")
        else:
            # 미체결(HOLD, SELL 차단 등): 로컬 파일만, git push 스킵
            subprocess.run(["git", "restore", "--staged", "docs/trades.json"], cwd=repo_root, check=False)
            log("  ℹ️  미체결/HOLD — trades.json 로컬 갱신 (GitHub push 스킵)")
    except Exception as e:
        log(f"  ⚠️  trades.json 업데이트 실패 (무시): {e}")


def daily_report():
    """매일 아침 어제 손익 + 누적 통계 ntfy 알림"""
    # 오늘 이미 발송했으면 스킵 (중복 방지)
    lock_file = os.path.join(os.path.dirname(__file__), "report_sent.txt")
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(lock_file):
        with open(lock_file) as f:
            if f.read().strip() == today:
                log("  📊 일일 리포트 — 오늘 이미 발송됨, 스킵")
                return
    with open(lock_file, "w") as f:
        f.write(today)

    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.path.dirname(__file__), text=True
        ).strip()
        trades_path = os.path.join(repo_root, "docs", "trades.json")

        if not os.path.exists(trades_path):
            notify("📊 일일 리포트", "거래 데이터 없음", priority="min")
            return

        with open(trades_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        stats  = data.get("stats", {})
        history = data.get("history", [])
        holding = data.get("holding")

        # 어제 날짜 거래만 필터
        yesterday = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                     .__class__.fromordinal(datetime.now().toordinal() - 1)).strftime("%Y-%m-%d")
        yesterday_trades = [t for t in history if t.get("time", "").startswith(yesterday)]
        yesterday_pnl = sum(t.get("pnl_krw") or 0 for t in yesterday_trades if t.get("action") == "SELL")

        total   = stats.get("total_trades", 0)
        wins    = stats.get("wins", 0)
        losses  = stats.get("losses", 0)
        total_pnl = stats.get("total_pnl_krw", 0)
        win_rate = round(wins / total * 100) if total > 0 else 0

        holding_line = f"보유 중: {holding['ticker']}" if holding else "보유 없음"
        yesterday_line = f"어제 손익: {'+' if yesterday_pnl >= 0 else ''}{yesterday_pnl:,.0f}원" if yesterday_trades else "어제 거래 없음"

        msg = (
            f"{yesterday_line}\n"
            f"누적 손익: {'+' if total_pnl >= 0 else ''}{total_pnl:,.0f}원\n"
            f"승률: {wins}승 {losses}패 ({win_rate}%)\n"
            f"총 거래: {total}회\n"
            f"{holding_line}"
        )
        notify("📊 일일 트레이딩 리포트", msg, priority="default")
        log(f"  📊 일일 리포트 발송 완료")
    except Exception as e:
        log(f"  ⚠️  일일 리포트 실패: {e}")


def ip_report():
    """IP 변경 감지 시에만 ntfy 알림 — 정상이면 스킵"""
    try:
        current_ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception as e:
        log(f"  ⚠️  IP 확인 실패: {e}")
        return

    prev_ip = None
    if os.path.exists(IP_FILE):
        with open(IP_FILE, "r") as f:
            prev_ip = f.read().strip()

    with open(IP_FILE, "w") as f:
        f.write(current_ip)

    if prev_ip and prev_ip != current_ip:
        log(f"  🔴 IP 변경: {prev_ip} → {current_ip}")
        notify(
            "🔴 IP 변경 감지 — API 키 재등록 필요",
            f"공인 IP가 변경됐습니다!\n이전: {prev_ip}\n현재: {current_ip}\n\n빗썸 API 키 IP 허용 목록을 업데이트하세요.",
            priority="urgent",
        )
    else:
        log(f"  🌐 IP 정상: {current_ip} (알림 스킵)")


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "report":
        daily_report()
    elif len(_sys.argv) > 1 and _sys.argv[1] == "ip":
        ip_report()
    else:
        try:
            main()
        except _TraderTimeout as e:
            log(f"  ❌ 실행 타임아웃: {e}")
            notify("❌ 자동매매 타임아웃", "10분 초과로 강제 종료됨 — 네트워크 확인 필요", priority="high")
        except Exception as e:
            log(f"  ❌ 예상치 못한 오류: {e}")
            notify("❌ 자동매매 오류", f"예상치 못한 오류: {e}", priority="high")
        finally:
            # lock 파일 반드시 삭제 (어떤 경우에도)
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass
