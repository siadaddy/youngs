"""
🧠 AI 어드바이저 거래 메모리
매 거래 결과를 누적 → 패턴 분석 → 프롬프트 자동 조정
"""
import os, json
from datetime import datetime, timedelta
from collections import Counter

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "advisor_memory.json")


def _load() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def remember(agent: str, event_type: str, data: dict, max_entries: int = 100):
    """경험 저장. 최신이 앞에, 최대 max_entries개 유지."""
    mem = _load()
    mem.setdefault(agent, {}).setdefault(event_type, [])
    entry = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), **data}
    mem[agent][event_type].insert(0, entry)
    mem[agent][event_type] = mem[agent][event_type][:max_entries]
    _save(mem)


def recall(agent: str, event_type: str, days: int = 14, limit: int = 50) -> list:
    """최근 N일치 경험 반환."""
    mem = _load()
    entries = mem.get(agent, {}).get(event_type, [])
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [e for e in entries if e.get("date", "")[:10] >= cutoff][:limit]


def get_hints(agent: str) -> str:
    """에이전트별 학습 힌트 반환 (프롬프트 주입용). 실패 시 빈 문자열."""
    try:
        if agent == "AI어드바이저":
            return _advisor_hints()
    except Exception as e:
        print(f"  ⚠️  [{agent}] 메모리 힌트 로드 실패 (무시): {e}")
    return ""


def _advisor_hints() -> str:
    outcomes = recall("AI어드바이저", "trade_outcome", days=14)
    if len(outcomes) < 3:
        return ""

    exit_counter = Counter()
    ticker_losses: Counter = Counter()

    for e in outcomes:
        exit_type = e.get("exit_type", "")
        pnl = e.get("pnl_pct", 0)
        ticker = e.get("ticker", "")
        exit_counter[exit_type] += 1
        if pnl < 0:
            ticker_losses[ticker] += 1

    total = len(outcomes)
    losses = sum(1 for e in outcomes if e.get("pnl_pct", 0) < 0)
    if losses == 0:
        return ""

    lines = [f"\n\n📚 [거래 메모리 — 최근 {total}건 분석]"]
    win_rate = round((total - losses) / total * 100)
    lines.append(f"  승률: {total - losses}/{total} ({win_rate}%)")

    if exit_counter.get("stop_loss", 0) >= 2:
        lines.append(f"  ⚠️  최근 손절 {exit_counter['stop_loss']}회 — ADX·거래량 조건 더 엄격히 적용할 것")
    if exit_counter.get("time_exit", 0) >= 2:
        lines.append(f"  ⚠️  시간초과 청산 {exit_counter['time_exit']}회 — 추세 없는 횡보 구간 진입 자제")

    problem_tickers = [(t, c) for t, c in ticker_losses.most_common(3) if c >= 2]
    if problem_tickers:
        t_str = ", ".join(f"{t}({c}회)" for t, c in problem_tickers)
        lines.append(f"  ⛔ 반복 손실 종목: {t_str} → 이번엔 진입 신중히")

    return "\n".join(lines)


def get_summary() -> list:
    """메모리 현황 요약 (CLI 확인용)."""
    mem = _load()
    if not mem:
        return ["📭 advisor_memory.json 비어 있음"]
    lines = ["🧠 AI 어드바이저 메모리 현황"]
    for agent, events in mem.items():
        for etype, entries in events.items():
            latest = entries[0]["date"] if entries else "N/A"
            lines.append(f"  {agent} / {etype}: {len(entries)}건 (최신: {latest})")
    return lines


# ── 자기 학습 — 페르소나 + 성장 일기 ─────────────────────────

INIT_PERSONAS = {
    "AI어드바이저": "나는 30분마다 시장을 분석하는 코인 트레이딩 AI야. 손절을 반복하며 어떤 종목과 패턴이 위험한지 배우고 있어. 빠른 판단보다 정확한 판단이 중요하다는 걸 깨닫는 중이야.",
}


def get_persona(agent: str) -> str:
    mem = _load()
    return mem.get(agent, {}).get("persona", INIT_PERSONAS.get(agent, ""))


def get_diary(agent: str, limit: int = 5) -> list:
    mem = _load()
    return mem.get(agent, {}).get("diary", [])[:limit]


def get_growth_score(agent: str) -> int:
    mem = _load()
    return mem.get(agent, {}).get("growth_score", 0)


def add_diary(agent: str, lesson: str, trigger: str = ""):
    mem = _load()
    mem.setdefault(agent, {})
    mem[agent].setdefault("diary", [])
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "lesson": lesson[:200],
        "trigger": trigger,
    }
    mem[agent]["diary"].insert(0, entry)
    mem[agent]["diary"] = mem[agent]["diary"][:60]
    mem[agent]["growth_score"] = mem[agent].get("growth_score", 0) + 1
    _save(mem)


def update_persona(agent: str, new_persona: str):
    mem = _load()
    mem.setdefault(agent, {})
    mem[agent]["persona"] = new_persona[:300]
    mem[agent]["persona_updated_at"] = datetime.now().strftime("%Y-%m-%d")
    _save(mem)


def should_update_persona(agent: str, min_diary: int = 5, min_days: int = 7) -> bool:
    mem = _load()
    data = mem.get(agent, {})
    if len(data.get("diary", [])) < min_diary:
        return False
    last = data.get("persona_updated_at", "2026-01-01")
    try:
        days = (datetime.now() - datetime.strptime(last, "%Y-%m-%d")).days
    except Exception:
        return True
    return days >= min_days
