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
NTFY_TOPIC   = os.getenv("NTFY_TOPIC", "siadad-aicrew")
STOP_LOSS    = float(os.getenv("STOP_LOSS_PCT", "5.0"))
TAKE_PROFIT  = float(os.getenv("TAKE_PROFIT_PCT", "10.0"))
DRY_RUN      = os.getenv("DRY_RUN", "true").lower() == "true"


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
            "🔴 IP 변경 감지",
            f"공인 IP가 변경됐습니다!\n이전: {prev_ip}\n현재: {current_ip}\n\n업비트 API 키 IP 재등록 필요:\nhttps://upbit.com/mypage/open_api_management",
            priority="urgent",
        )
    else:
        log(f"  🌐 현재 IP: {current_ip}")


# ── 손절 / 익절 체크 ──────────────────────────────────────

def check_exit(holding: dict) -> str | None:
    """손절 또는 익절 조건 확인 → 'stop_loss' | 'take_profit' | None"""
    from utils.upbit_client import get_current_price
    now = get_current_price(holding["ticker"])
    if not now or not holding.get("buy_price"):
        return None
    pct = (now / holding["buy_price"] - 1) * 100
    if pct <= -STOP_LOSS:
        log(f"  🔴 손절 발동: {holding['ticker']} | {pct:.2f}% (기준: -{STOP_LOSS}%)")
        return "stop_loss"
    if pct >= TAKE_PROFIT:
        log(f"  🟡 익절 발동: {holding['ticker']} | {pct:.2f}% (기준: +{TAKE_PROFIT}%)")
        return "take_profit"
    return None


# ── 메인 ─────────────────────────────────────────────────

def _timeout_handler(signum, frame):
    raise TimeoutError("전체 실행 10분 초과 — 강제 종료")


def main():
    # 전체 실행 타임아웃 10분 (네트워크 hang 방지)
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(600)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    dry_tag = " [DRY RUN]" if DRY_RUN else ""
    log(f"\n{'='*55}")
    log(f"🤖 AI 코인 자동매매 시작 — {now_str}{dry_tag}")
    log(f"{'='*55}")

    # Step 0: 이전 실패 체크 + IP 변경 감지
    check_and_notify_failures()
    check_ip_change()

    # Step 1: 보유 상태 로드
    holding = load_state()
    if holding:
        log(f"  📦 현재 보유: {holding['ticker']} | 매수가 {holding['buy_price']:,.0f}원 | {holding['qty']:.8f}개")
    else:
        log("  📦 현재 보유 종목 없음")

    # Step 2: 손절 / 익절 체크 (보유 중일 때)
    if holding:
        try:
            exit_type = check_exit(holding)
        except Exception as e:
            log(f"  ⚠️  손절/익절 체크 실패 (무시하고 계속): {e}")
            exit_type = None
        if exit_type == "stop_loss":
            action = {"action": "SELL", "ticker": holding["ticker"], "reason": f"자동 손절 -{STOP_LOSS}%"}
            try:
                new_holding = executor.run(action, holding)
                save_state(new_holding)
                notify("🔴 손절 매도", f"{action['ticker']} 손절 매도 완료\n기준: -{STOP_LOSS}%", priority="high")
                _publish_trades("SELL", action, new_holding, load_state())
            except Exception as e:
                log(f"  ❌ 손절 매도 실패: {e}")
                notify("❌ 손절 실패", f"{holding['ticker']} 손절 주문 오류: {e}", priority="urgent")
            log("  손절 처리 완료 — 이번 사이클 종료")
            return
        elif exit_type == "take_profit":
            action = {"action": "SELL", "ticker": holding["ticker"], "reason": f"자동 익절 +{TAKE_PROFIT}%"}
            try:
                new_holding = executor.run(action, holding)
                save_state(new_holding)
                notify("🟡 익절 매도", f"{action['ticker']} 익절 매도 완료\n기준: +{TAKE_PROFIT}%", priority="high")
                _publish_trades("SELL", action, new_holding, holding)
            except Exception as e:
                log(f"  ❌ 익절 매도 실패: {e}")
                notify("❌ 익절 실패", f"{holding['ticker']} 익절 주문 오류: {e}", priority="urgent")
            log("  익절 처리 완료 — 이번 사이클 종료")
            return

    # Step 3: 시장 분석
    try:
        market_data = retry("시장 분석", analyzer.run)
    except Exception as e:
        is_network = "NameResolution" in str(e) or "Failed to resolve" in str(e) or "timed out" in str(e).lower()
        record_failure("네트워크 실패" if is_network else f"시장분석 실패: {e}")
        notify("❌ 자동매매 오류", f"시장 분석 실패: {e}", priority="high")
        return

    # Step 4: AI 판단
    try:
        advice = retry("AI 판단", ai_advisor.run, market_data, holding)
    except Exception as e:
        record_failure(f"AI판단 실패: {e}")
        notify("❌ 자동매매 오류", f"AI 판단 실패: {e}", priority="high")
        return

    # Step 5: 주문 실행
    try:
        new_holding = executor.run(advice, holding)
    except Exception as e:
        log(f"  ❌ 주문 실행 실패: {e}")
        notify("❌ 자동매매 오류", f"주문 실행 실패: {e}", priority="high")
        return

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
            from utils.upbit_client import get_current_price
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
            elif action == "BUY" and new_holding:
                data["stats"]["total_trades"] += 1

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

        # git push (BUY/SELL만 — HOLD는 updated_at 갱신만하고 push 스킵)
        ticker_str = advice.get("ticker") or (new_holding["ticker"] if new_holding else "")
        dry_str = " [DRY]" if DRY_RUN else ""
        subprocess.run(["git", "add", "docs/trades.json"], cwd=repo_root, check=True)
        if action in ("BUY", "SELL"):
            subprocess.run(
                ["git", "commit", "-m", f"trade: {now_str} {action} {ticker_str}{dry_str}"],
                cwd=repo_root, check=True
            )
            subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
            log("  ✅ trades.json GitHub 업데이트 완료")
        else:
            # HOLD: local 파일만 업데이트, git push 스킵 (불필요한 commit 방지)
            subprocess.run(["git", "restore", "--staged", "docs/trades.json"], cwd=repo_root, check=False)
            log("  ℹ️  HOLD — trades.json 로컬 갱신 (GitHub push 스킵)")
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
    """거래 1시간 전 현재 IP 알림 (업비트 API 키 IP 점검용)"""
    try:
        current_ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception as e:
        notify("⚠️ IP 확인 실패", f"IP 조회 오류: {e}", priority="high")
        return

    prev_ip = None
    if os.path.exists(IP_FILE):
        with open(IP_FILE, "r") as f:
            prev_ip = f.read().strip()

    if prev_ip and prev_ip != current_ip:
        status = f"🔴 IP 변경됨!\n이전: {prev_ip}\n현재: {current_ip}\n\n업비트 API 키 재등록 필요"
        priority = "urgent"
    else:
        status = f"✅ IP 정상\n현재: {current_ip}"
        priority = "min"

    next_trade = (datetime.now().hour + 1) % 24
    notify(
        f"🕐 1시간 후 코인 트레이딩 예정",
        f"{status}\n\n다음 거래: {next_trade:02d}:05",
        priority=priority,
    )
    log(f"  📡 IP 사전 점검 알림 발송: {current_ip}")


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "report":
        daily_report()
    elif len(_sys.argv) > 1 and _sys.argv[1] == "ip":
        ip_report()
    else:
        try:
            main()
        except TimeoutError as e:
            log(f"  ❌ 실행 타임아웃: {e}")
            notify("❌ 자동매매 타임아웃", "10분 초과로 강제 종료됨 — 네트워크 확인 필요", priority="high")
        except Exception as e:
            log(f"  ❌ 예상치 못한 오류: {e}")
            notify("❌ 자동매매 오류", f"예상치 못한 오류: {e}", priority="high")
