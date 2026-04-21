#!/usr/bin/env python3
"""
🛡️ 가격 감시 데몬
━━━━━━━━━━━━━━━━━━━━━━━━
30초마다 보유 종목 현재가 체크 → 손절/익절 즉시 실행
launchd KeepAlive로 상시 실행됨
"""

import os, sys, json, time, requests, subprocess
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

STATE_FILE     = os.path.join(os.path.dirname(__file__), "state.json")
COOLDOWN_FILE  = os.path.join(os.path.dirname(__file__), "cooldown.json")
LOCK_FILE      = os.path.join(os.path.dirname(__file__), "main.lock")
LOG_FILE       = os.path.join(os.path.dirname(__file__), "trader.log")
NTFY_TOPIC     = os.getenv("NTFY_TOPIC", "siadad-aicrew")
STOP_LOSS      = float(os.getenv("STOP_LOSS_PCT", "4.0"))
TAKE_PROFIT    = float(os.getenv("TAKE_PROFIT_PCT", "5.0"))
DRY_RUN        = os.getenv("DRY_RUN", "true").lower() == "true"
INTERVAL       = 30  # 체크 간격 (초)
COOLDOWN_HOURS        = 6  # 손절 종목 재진입 금지 (3→6시간)
GLOBAL_COOLDOWN_HOURS = 4  # 전역 매수 금지 (2→4시간)


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


def execute_sell(holding: dict, reason: str) -> dict | None:
    try:
        from agents import executor
        action = {"action": "SELL", "ticker": holding["ticker"], "reason": reason}
        new_holding = executor.run(action, holding)
        save_state(new_holding)
        return new_holding
    except Exception as e:
        log(f"  ❌ 매도 실행 실패: {e}")
        return holding


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
    global STOP_LOSS, TAKE_PROFIT
    dry_tag = " [DRY RUN]" if DRY_RUN else ""
    log(f"🛡️ 가격 감시 시작{dry_tag} | 손절 -{STOP_LOSS}% | 익절 +{TAKE_PROFIT}% | {INTERVAL}초 간격")

    while True:
        try:
            # .env 매 루프마다 재로드 — 설정 변경 즉시 반영
            load_dotenv(override=True)
            STOP_LOSS   = float(os.getenv("STOP_LOSS_PCT", "4.0"))
            TAKE_PROFIT = float(os.getenv("TAKE_PROFIT_PCT", "8.0"))

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

            if pct <= -STOP_LOSS:
                log(f"🔴 손절 발동: {holding['ticker']} | {pct:.2f}% | 현재가 {price:,.0f}원")
                reason = f"실시간 손절 {pct:.2f}% (기준 -{STOP_LOSS}%)"
                new_holding = execute_sell(holding, reason)
                add_cooldown(holding["ticker"])  # 종목 쿨다운 + 전역 쿨다운 등록
                notify(
                    f"🔴 손절 매도{dry_tag}",
                    f"{holding['ticker']} 실시간 손절\n수익률: {pct:.2f}%\n현재가: {price:,.0f}원\n⛔ {GLOBAL_COOLDOWN_HOURS}시간 매수 금지",
                    priority="urgent"
                )
                publish_trade("SELL", holding, new_holding, reason, price)

            elif pct >= TAKE_PROFIT:
                log(f"🟡 익절 발동: {holding['ticker']} | {pct:.2f}% | 현재가 {price:,.0f}원")
                reason = f"실시간 익절 {pct:.2f}% (기준 +{TAKE_PROFIT}%)"
                new_holding = execute_sell(holding, reason)
                notify(
                    f"🟡 익절 매도{dry_tag}",
                    f"{holding['ticker']} 실시간 익절\n수익률: {pct:.2f}%\n현재가: {price:,.0f}원",
                    priority="high"
                )
                publish_trade("SELL", holding, new_holding, reason, price)

        except Exception as e:
            log(f"⚠️ 감시 루프 오류 (계속 실행): {e}")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
