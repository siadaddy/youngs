"""
AI 사무실 학습 기록 export — coin-trader 측
trades.json + blacklist.json + advisor_memory.json → docs/office_memory.json
"""
import os, json, re
from datetime import datetime

REPO_ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TRADES_FILE    = os.path.join(REPO_ROOT, "docs", "trades.json")
OFFICE_FILE    = os.path.join(REPO_ROOT, "docs", "office_memory.json")
BLACKLIST_FILE = os.path.join(os.path.dirname(__file__), "..", "blacklist.json")
ADVISOR_FILE   = os.path.join(os.path.dirname(__file__), "..", "advisor_memory.json")


def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _advisor_diary():
    """advisor_memory.json에서 AI어드바이저 diary/persona 로드"""
    try:
        from utils.agent_memory import get_diary, get_persona, get_growth_score
        return (get_diary("AI어드바이저", 3),
                get_persona("AI어드바이저")[:60],
                get_growth_score("AI어드바이저"))
    except Exception:
        return [], "", 0


def _advisor_data():
    trades    = _load(TRADES_FILE)
    blacklist = _load(BLACKLIST_FILE)
    history   = trades.get("history", [])
    stats     = trades.get("stats", {})
    holding   = trades.get("holding")

    total    = stats.get("total_trades", 0)
    wins     = stats.get("wins", 0)
    losses   = stats.get("losses", 0)
    win_rate = round(wins / total * 100) if total > 0 else 0

    # 최근 5건
    recent = []
    for h in history[:8]:
        if h.get("action") not in ("BUY", "SELL"):
            continue
        pnl = h.get("pnl_pct")
        entry = {
            "time":   h["time"][-5:],
            "date":   h["time"][:10],
            "ticker": h.get("ticker", ""),
            "pnl":    pnl,
            "action": h.get("action"),
        }
        if h.get("action") == "SELL" and pnl is not None:
            reason = h.get("reason", "")
            if pnl <= -3.5 or "손절" in reason:
                entry["type"] = "stop_loss"
            elif pnl > 0:
                entry["type"] = "take_profit"
            else:
                entry["type"] = "force_exit"
        recent.append(entry)

    # 블랙리스트 요약
    bl_list = []
    for ticker, info in sorted(blacklist.items(), key=lambda x: -x[1].get("stop_loss_count", 0)):
        cnt   = info.get("stop_loss_count", 0)
        until = info.get("blacklisted_until")
        if until:
            bl_list.append(f"{ticker}({cnt}회 차단)")
        elif cnt >= 2:
            bl_list.append(f"{ticker}({cnt}회)")

    # 학습 힌트
    sells       = [h for h in history[:20] if h.get("action") == "SELL" and h.get("pnl_pct") is not None]
    stop_losses = [h for h in sells if h.get("pnl_pct", 0) <= -3.5]
    time_exits  = [h for h in sells if "시간" in h.get("reason", "")]
    hints = []
    if len(stop_losses) >= 2:
        hints.append(f"⚠️ 최근 손절 {len(stop_losses)}회 — ADX·거래량 조건 강화")
    if len(time_exits) >= 2:
        hints.append(f"⚠️ 강제청산 {len(time_exits)}회 — 횡보 구간 진입 자제")
    if bl_list:
        hints.append(f"🚫 차단 종목: {', '.join(bl_list[:2])}")

    # 보유 중
    holding_txt = f"📊 {holding['ticker']} 보유 중" if holding else "💤 현재 보유 없음"

    last_active = history[0]["time"] if history else ""
    diary, persona, score = _advisor_diary()

    return {
        "win_rate":    win_rate,
        "total":       total,
        "wins":        wins,
        "losses":      losses,
        "holding":     holding_txt,
        "hint":        " | ".join(hints) if hints else f"✅ 승률 {win_rate}% 유지 중",
        "blacklist":   bl_list[:4],
        "recent":      recent[:5],
        "last_active": last_active,
        "diary":       diary,
        "persona":     persona,
        "growth_score": score,
    }


def _trade_log():
    trades  = _load(TRADES_FILE)
    history = trades.get("history", [])
    log = []
    for h in history[:20]:
        action = h.get("action", "")
        ticker = h.get("ticker", "")
        pnl    = h.get("pnl_pct")
        reason = h.get("reason", "")

        if action == "BUY":
            signals = []
            m = re.search(r'RSI[는이]?\s*([\d.]+)', reason)
            if m: signals.append(f"RSI {m.group(1)}")
            m = re.search(r'ADX[는이]?\s*([\d.]+)', reason)
            if m: signals.append(f"ADX {m.group(1)}")
            m = re.search(r'거래량.*?([\d]+)%', reason)
            if m: signals.append(f"거래량+{m.group(1)}%")
            sig = "·".join(signals[:2]) if signals else "진입"
            msg = f"{ticker} 매수 — {sig}"
            log_type = "buy"
        elif action == "SELL" and pnl is not None:
            if pnl > 0:
                msg, log_type = f"{ticker} 익절 +{pnl}% 🎯", "win"
            elif pnl <= -3.5 or "손절" in reason:
                msg, log_type = f"{ticker} 손절 {pnl}% → 학습 기록 🚫", "loss"
            elif "시간" in reason:
                msg, log_type = f"{ticker} 강제청산 {pnl:+.1f}% (8시간)", "exit"
            else:
                msg, log_type = f"{ticker} 매도 {pnl:+.1f}%", "sell"
        else:
            continue

        log.append({
            "time":  h.get("time", ""),
            "agent": "AI어드바이저",
            "icon":  "🤖",
            "msg":   msg,
            "type":  log_type,
        })
    return log


def export():
    """office_memory.json 에 AI어드바이저 데이터 병합 저장"""
    existing = _load(OFFICE_FILE) if os.path.exists(OFFICE_FILE) else {}
    agents   = existing.get("agents", {})
    agents["AI어드바이저"] = _advisor_data()

    trade_log    = _trade_log()
    other_log    = [e for e in existing.get("log", []) if e.get("agent") != "AI어드바이저"]
    all_log      = trade_log + other_log
    all_log.sort(key=lambda x: x.get("time", ""), reverse=True)

    out = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "agents":  agents,
        "log":     all_log[:50],
    }
    with open(OFFICE_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
