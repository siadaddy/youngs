#!/usr/bin/env python3
"""
⚡ 실시간 손절/익절 모니터
5분마다 현재가를 체크해 손절(-7%) 또는 익절(+15%) 즉시 실행
AI 분석 없이 가격 확인만 → 빠른 대응
"""

import os, sys, json, subprocess, requests, signal
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
STATE_FILE   = os.path.join(BASE_DIR, "state.json")
LOCK_FILE    = os.path.join(BASE_DIR, "main.lock")
STOP_LOSS    = float(os.getenv("STOP_LOSS_PCT", "7.0"))
TAKE_PROFIT  = float(os.getenv("TAKE_PROFIT_PCT", "15.0"))
NTFY_TOPIC   = os.getenv("NTFY_TOPIC", "siadad-aicrew")
DRY_RUN      = os.getenv("DRY_RUN", "true").lower() == "true"


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def notify(title: str, message: str, priority: str = "default"):
    priority_map = {"min": 1, "default": 3, "high": 4, "urgent": 5}
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


def load_holding() -> dict | None:
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


def publish_sell(new_holding: dict | None, old_holding: dict, reason: str):
    """매도 결과를 trades.json에 기록하고 GitHub에 push"""
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=BASE_DIR, text=True
        ).strip()
        trades_path = os.path.join(repo_root, "docs", "trades.json")

        if not os.path.exists(trades_path):
            return

        with open(trades_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        if new_holding is None:
            from utils.bithumb_client import get_current_price
            ticker   = old_holding["ticker"]
            price    = get_current_price(ticker)
            buy_p    = old_holding.get("buy_price", 0)
            qty      = old_holding.get("qty", 0)
            pnl_pct  = round((price / buy_p - 1) * 100, 2) if buy_p else 0
            pnl_krw  = round((price - buy_p) * qty, 0) if buy_p else 0

            data["stats"]["total_trades"] = data["stats"].get("total_trades", 0) + 1
            if pnl_pct >= 0:
                data["stats"]["wins"] = data["stats"].get("wins", 0) + 1
            else:
                data["stats"]["losses"] = data["stats"].get("losses", 0) + 1
            data["stats"]["total_pnl_krw"] = round(
                data["stats"].get("total_pnl_krw", 0) + pnl_krw, 0
            )

            entry = {
                "time":       now_str,
                "action":     "SELL",
                "ticker":     ticker,
                "price":      price,
                "amount_krw": old_holding.get("invest_krw", 0),
                "reason":     reason,
                "pnl_pct":    pnl_pct,
                "pnl_krw":    pnl_krw,
                "dry_run":    DRY_RUN,
            }
            data["history"].insert(0, entry)
            data["history"] = data["history"][:50]

        data["holding"]    = new_holding
        data["updated_at"] = now_str

        with open(trades_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if new_holding is None:
            dry_str = " [DRY]" if DRY_RUN else ""
            subprocess.run(["git", "add", "docs/trades.json"], cwd=repo_root, check=True)
            subprocess.run(
                ["git", "commit", "-m",
                 f"monitor: {now_str} SELL {old_holding['ticker']}{dry_str}"],
                cwd=repo_root, check=True
            )
            subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
            log("  ✅ trades.json GitHub 업데이트 완료")

    except Exception as e:
        log(f"  ⚠️  trades.json 업데이트 실패: {e}")


def try_sell(holding: dict, reason: str) -> dict | None:
    """매도 실행 후 새 holding 반환 (None = 매도 완료)"""
    from agents import executor
    action = {"action": "SELL", "ticker": holding["ticker"], "reason": reason}
    new_holding = executor.run(action, holding)
    save_state(new_holding)
    publish_sell(new_holding, holding, reason)
    return new_holding


def main():
    signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError("모니터 타임아웃")))
    signal.alarm(90)  # 1.5분 타임아웃 (5분 주기보다 짧게)

    # .env 매 실행마다 재로드 — 설정 변경 즉시 반영
    load_dotenv(override=True)
    global STOP_LOSS, TAKE_PROFIT
    STOP_LOSS   = float(os.getenv("STOP_LOSS_PCT", "7.0"))
    TAKE_PROFIT = float(os.getenv("TAKE_PROFIT_PCT", "15.0"))

    log("⚡ 가격 모니터 실행")

    # main.py가 실행 중이면 스킵 (lock 파일 확인)
    if os.path.exists(LOCK_FILE):
        log("⏭  main.py 실행 중 감지 — 모니터 스킵")
        return

    holding = load_holding()
    if not holding:
        log("📭 보유 종목 없음 — 스킵")
        return

    ticker    = holding["ticker"]
    buy_price = holding.get("buy_price", 0)
    if not buy_price:
        log("⚠️  매수가 정보 없음 — 스킵")
        return

    # 현재가 조회
    try:
        from utils.bithumb_client import get_current_price
        price = get_current_price(ticker)
    except Exception as e:
        log(f"⚠️  가격 조회 실패: {e}")
        return

    if not price:
        log("⚠️  가격 조회 실패 (0 반환)")
        return

    pct = (price / buy_price - 1) * 100
    log(f"📊 {ticker} | 현재가 {price:,.0f}원 | 수익률 {pct:+.2f}%  "
        f"(손절 -{STOP_LOSS}% / 익절 +{TAKE_PROFIT}%)")

    if pct <= -STOP_LOSS:
        log(f"🔴 손절 발동! {pct:+.2f}%")
        reason = f"실시간 손절: {pct:+.2f}% ≤ -{STOP_LOSS}%"
        new_holding = try_sell(holding, reason)
        if new_holding is None:
            notify(
                f"🔴 손절 완료 (실시간 모니터)",
                f"{ticker} 즉시 매도\n수익률: {pct:+.2f}%\n현재가: {price:,.0f}원",
                priority="urgent",
            )
            log("  ✅ 손절 매도 완료")
        else:
            notify(
                f"⚠️ 손절 시도 실패",
                f"{ticker} 손절 조건 충족 ({pct:+.2f}%)이나 최소금액 미달\n현재가: {price:,.0f}원",
                priority="high",
            )
            log("  ⚠️  손절 매도 미체결 — 최소금액 미달")

    elif pct >= TAKE_PROFIT:
        log(f"🟡 익절 발동! {pct:+.2f}%")
        reason = f"실시간 익절: {pct:+.2f}% ≥ +{TAKE_PROFIT}%"
        new_holding = try_sell(holding, reason)
        if new_holding is None:
            notify(
                f"🟡 익절 완료 (실시간 모니터)",
                f"{ticker} 즉시 매도\n수익률: {pct:+.2f}%\n현재가: {price:,.0f}원",
                priority="high",
            )
            log("  ✅ 익절 매도 완료")
        else:
            log("  ⚠️  익절 매도 미체결 — 최소금액 미달")

    else:
        log("  ✅ 정상 범위 — 대기")

    signal.alarm(0)


if __name__ == "__main__":
    try:
        main()
    except TimeoutError as e:
        log(f"  ❌ 타임아웃: {e}")
    except Exception as e:
        log(f"  ❌ 오류: {e}")
