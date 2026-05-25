#!/usr/bin/env python3
"""
🛡️ 가격 감시 데몬
━━━━━━━━━━━━━━━━━━━━━━━━
30초마다 보유 종목 현재가 체크 → 손절/익절 즉시 실행
launchd KeepAlive로 상시 실행됨
"""

import os, sys, json, time, requests, subprocess
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

STATE_FILE     = os.path.join(os.path.dirname(__file__), "state.json")
COOLDOWN_FILE  = os.path.join(os.path.dirname(__file__), "cooldown.json")
DRAWDOWN_FILE  = os.path.join(os.path.dirname(__file__), "drawdown.json")
LOCK_FILE      = os.path.join(os.path.dirname(__file__), "main.lock")
LOG_FILE       = os.path.join(os.path.dirname(__file__), "trader.log")
NTFY_TOPIC            = os.getenv("NTFY_TOPIC", "siadad-aicrew")
STOP_LOSS             = float(os.getenv("STOP_LOSS_PCT", "4.0"))
TAKE_PROFIT           = float(os.getenv("TAKE_PROFIT_PCT", "5.0"))   # ★ 기본값 8.0→5.0 수정
TRAILING_STOP_PCT     = float(os.getenv("TRAILING_STOP_PCT", "2.5"))
TRAILING_ACTIVATE     = float(os.getenv("TRAILING_ACTIVATE_PCT", "3.0"))
DAILY_LOSS_LIMIT      = float(os.getenv("DAILY_LOSS_LIMIT_KRW", "-7500"))
DRY_RUN               = os.getenv("DRY_RUN", "true").lower() == "true"
INTERVAL              = 30   # 체크 간격 (초)
COOLDOWN_HOURS        = 6    # 손절 종목 재진입 금지
GLOBAL_COOLDOWN_HOURS = 4    # 전역 매수 금지


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [GUARD] {msg}", flush=True)  # plist StandardOutPath → trader.log


def notify(title: str, message: str, priority: str = "default"):
    priority_map = {"default": 3, "high": 4, "urgent": 5, "min": 1}
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
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data.get("ticker") else None
    except Exception:
        return None


def save_state(holding: dict | None):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(holding or {}, f, ensure_ascii=False, indent=2)


def get_price(ticker: str) -> float | None:
    try:
        from utils.bithumb_client import get_current_price
        price = get_current_price(ticker)
        return price if price else None
    except Exception:
        return None


def add_cooldown(ticker: str):
    """손절 후 종목 쿨다운 + 전역 쿨다운 등록 (main.py와 공유)"""
    try:
        from datetime import timedelta
        data = {}
        if os.path.exists(COOLDOWN_FILE):
            with open(COOLDOWN_FILE, "r") as f:
                data = json.load(f)
        now = datetime.now()
        ticker_until = (now + timedelta(hours=COOLDOWN_HOURS)).strftime("%Y-%m-%d %H:%M")
        global_until = (now + timedelta(hours=GLOBAL_COOLDOWN_HOURS)).strftime("%Y-%m-%d %H:%M")
        data[ticker]    = ticker_until
        data["_global"] = global_until
        with open(COOLDOWN_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"  ⛔ 종목 쿨다운: {ticker} → {ticker_until}까지")
        log(f"  🚫 전역 쿨다운: 모든 BUY → {global_until}까지 금지")
    except Exception as e:
        log(f"  ⚠️  쿨다운 등록 실패: {e}")


def _record_loss(holding: dict, sell_price: float):
    """손절 실제 PnL 기록 — drawdown.json 누적 (main.py record_loss와 동일 로직)"""
    try:
        if not holding.get("buy_price") or not holding.get("qty"):
            return
        pnl_krw = round((sell_price - holding["buy_price"]) * holding["qty"], 0)
        if pnl_krw >= 0:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        data = {"date": today, "daily_loss_krw": 0.0, "paused": False}
        if os.path.exists(DRAWDOWN_FILE):
            try:
                with open(DRAWDOWN_FILE, "r") as f:
                    d = json.load(f)
                if d.get("date") == today:
                    data = d
            except Exception:
                pass
        data["daily_loss_krw"] += pnl_krw
        if data["daily_loss_krw"] <= DAILY_LOSS_LIMIT:
            data["paused"] = True
            log(f"  🛑 Daily Drawdown Limit reached! 누적 손실 {data['daily_loss_krw']:,.0f}원 — bot paused")
            notify("🛑 일일 손실 한도 도달",
                   f"오늘 누적 손실: {data['daily_loss_krw']:,.0f}원\n한도: {DAILY_LOSS_LIMIT:,.0f}원\n봇이 오늘 하루 정지됩니다.",
                   priority="urgent")
        with open(DRAWDOWN_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"  📉 손실 기록: {pnl_krw:,.0f}원 | 오늘 누적: {data['daily_loss_krw']:,.0f}원")
    except Exception as e:
        log(f"  ⚠️  손실 기록 실패: {e}")


def execute_sell(holding: dict, reason: str, force: bool = False) -> dict | None:
    """매도 실행 — 최대 3회 재시도. force=True면 최소금액 체크 무시"""
    last_err = None
    for attempt in range(1, 4):
        try:
            from agents import executor
            action = {"action": "SELL", "ticker": holding["ticker"], "reason": reason, "force": force}
            new_holding = executor.run(action, holding)
            save_state(new_holding)
            return new_holding
        except Exception as e:
            last_err = e
            log(f"  ❌ 매도 실행 실패 ({attempt}/3): {e}")
            if attempt < 3:
                time.sleep(3)
    log(f"  ❌ 매도 3회 모두 실패 — 다음 사이클에 재시도: {last_err}")
    return holding  # 원래 holding 유지 → 다음 30초 사이클에 자동 재시도


def publish_trade(action: str, holding: dict, new_holding: dict | None, reason: str, price: float):
    """trades.json 업데이트 & GitHub push"""
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.path.dirname(__file__), text=True
        ).strip()
        trades_path = os.path.join(repo_root, "docs", "trades.json")

        if os.path.exists(trades_path):
            with open(trades_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"holding": None, "history": [], "stats": {
                "total_trades": 0, "wins": 0, "losses": 0,
                "total_pnl_krw": 0, "start_date": datetime.now().strftime("%Y-%m-%d")
            }}

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        pnl_pct = round((price / holding["buy_price"] - 1) * 100, 2) if holding.get("buy_price") else None
        pnl_krw = round((price - holding["buy_price"]) * holding.get("qty", 0), 0) if holding.get("buy_price") else None

        data["stats"]["total_trades"] += 1
        if pnl_pct and pnl_pct >= 0:
            data["stats"]["wins"] += 1
        else:
            data["stats"]["losses"] += 1
        data["stats"]["total_pnl_krw"] = round(data["stats"].get("total_pnl_krw", 0) + (pnl_krw or 0), 0)

        data["history"].insert(0, {
            "time": now_str, "action": action,
            "ticker": holding["ticker"], "price": price,
            "amount_krw": holding.get("invest_krw", 0),
            "reason": reason, "pnl_pct": pnl_pct, "pnl_krw": pnl_krw,
            "dry_run": DRY_RUN,
        })
        data["history"] = data["history"][:50]
        data["holding"] = new_holding
        data["updated_at"] = now_str

        # 블랙리스트 현황 포함 (웹사이트 표시용)
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from utils.blacklist import load_blacklist
            data["blacklist"] = load_blacklist()
        except Exception:
            pass

        with open(trades_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        subprocess.run(["git", "add", "docs/trades.json"], cwd=repo_root, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"trade: {now_str} {action} {holding['ticker']} [GUARD]"],
            cwd=repo_root, check=True
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
    except Exception as e:
        log(f"  ⚠️  trades.json 업데이트 실패: {e}")


def main():
    global STOP_LOSS, TAKE_PROFIT, TRAILING_STOP_PCT, TRAILING_ACTIVATE
    dry_tag = " [DRY RUN]" if DRY_RUN else ""
    log(f"🛡️ 가격 감시 시작{dry_tag} | 손절 -{STOP_LOSS}% | 익절 +{TAKE_PROFIT}% | 트레일링 +{TRAILING_ACTIVATE}%/-{TRAILING_STOP_PCT}% | {INTERVAL}초 간격")

    while True:
        try:
            # .env 매 루프마다 재로드 — 설정 변경 즉시 반영
            load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
            STOP_LOSS         = float(os.getenv("STOP_LOSS_PCT", "2.5"))
            TAKE_PROFIT       = float(os.getenv("TAKE_PROFIT_PCT", "6.0"))
            TRAILING_STOP_PCT = float(os.getenv("TRAILING_STOP_PCT", "1.5"))
            TRAILING_ACTIVATE = float(os.getenv("TRAILING_ACTIVATE_PCT", "4.5"))

            # main.py 실행 중이면 스킵 (매매 충돌 방지)
            if os.path.exists(LOCK_FILE):
                time.sleep(INTERVAL)
                continue

            holding = load_state()

            if not holding:
                time.sleep(INTERVAL)
                continue

            price = get_price(holding["ticker"])
            if not price or not holding.get("buy_price"):
                time.sleep(INTERVAL)
                continue

            pct = (price / holding["buy_price"] - 1) * 100

            # ── 고점 갱신 (트레일링스탑 정확도 향상) ──────────────
            if price > holding.get("high_price", holding["buy_price"]):
                holding["high_price"] = price
                save_state(holding)

            # ── 1. 손절 ───────────────────────────────────────────
            if pct <= -STOP_LOSS:
                log(f"🔴 손절 발동: {holding['ticker']} | {pct:.2f}% | 현재가 {price:,.0f}원")
                reason = f"실시간 손절 {pct:.2f}% (기준 -{STOP_LOSS}%)"
                new_holding = execute_sell(holding, reason, force=True)
                if new_holding is None:
                    # ★ 실제 매도 완료 → 블랙리스트 학습 + 손실 기록 (누락 버그 수정)
                    try:
                        from utils.blacklist import register_stop_loss
                        bl_entry = register_stop_loss(holding["ticker"])
                        if bl_entry.get("blacklisted_until"):
                            notify(
                                f"📚 블랙리스트 등록: {holding['ticker']}",
                                f"손절 {bl_entry['stop_loss_count']}회 → 차단 (해제: {bl_entry['blacklisted_until']})",
                                priority="high"
                            )
                    except Exception as e:
                        log(f"  ⚠️  블랙리스트 기록 실패: {e}")
                    _record_loss(holding, price)
                add_cooldown(holding["ticker"])
                notify(
                    f"🔴 손절 매도{dry_tag}",
                    f"{holding['ticker']} 실시간 손절\n수익률: {pct:.2f}%\n현재가: {price:,.0f}원\n⛔ {GLOBAL_COOLDOWN_HOURS}시간 매수 금지",
                    priority="urgent"
                )
                publish_trade("SELL", holding, new_holding, reason, price)

            # ── 2. 익절 ───────────────────────────────────────────
            elif pct >= TAKE_PROFIT:
                log(f"🟡 익절 발동: {holding['ticker']} | {pct:.2f}% | 현재가 {price:,.0f}원")
                reason = f"실시간 익절 {pct:.2f}% (기준 +{TAKE_PROFIT}%)"
                new_holding = execute_sell(holding, reason)
                if new_holding is None:
                    # 수익 거래 → 블랙리스트 복구 카운트
                    try:
                        from utils.blacklist import add_successful_trade
                        add_successful_trade(holding["ticker"])
                    except Exception:
                        pass
                notify(
                    f"🟡 익절 매도{dry_tag}",
                    f"{holding['ticker']} 실시간 익절\n수익률: {pct:.2f}%\n현재가: {price:,.0f}원",
                    priority="high"
                )
                publish_trade("SELL", holding, new_holding, reason, price)

            # ── 3. 트레일링 스탑 (+TRAILING_ACTIVATE% 이상 수익 구간에서 활성) ──
            else:
                high = holding.get("high_price", holding["buy_price"])
                high_pct = (high / holding["buy_price"] - 1) * 100
                if high_pct >= TRAILING_ACTIVATE:
                    trail_pct = (price / high - 1) * 100
                    if trail_pct <= -TRAILING_STOP_PCT:
                        log(f"🟠 트레일링 스탑: {holding['ticker']} | 고점 {high:,.0f}원 대비 {trail_pct:.2f}% 하락 | 현재가 {price:,.0f}원")
                        reason = f"실시간 트레일링 스탑 (고점 {high:,.0f}원 대비 {trail_pct:.2f}%)"
                        new_holding = execute_sell(holding, reason)
                        if new_holding is None:
                            try:
                                from utils.blacklist import add_successful_trade
                                add_successful_trade(holding["ticker"])
                            except Exception:
                                pass
                        notify(
                            f"🟠 트레일링 익절{dry_tag}",
                            f"{holding['ticker']} 트레일링 스탑\n수익률: {pct:.2f}%\n고점 대비: {trail_pct:.2f}%\n현재가: {price:,.0f}원",
                            priority="high"
                        )
                        publish_trade("SELL", holding, new_holding, reason, price)

        except Exception as e:
            log(f"⚠️ 감시 루프 오류 (계속 실행): {e}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
