"""
🧠 AI 직원 공통 메모리 시스템 — Supabase 연동
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
agent_memories 테이블에 에이전트별 학습 데이터 저장.
events(jsonb): event_type별 경험 데이터
diary(jsonb):  성장 일기
persona(text): 현재 페르소나
growth_score:  성장 점수
"""

import os, json, re
from datetime import datetime, timedelta
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client():
    global _client
    if _client is None:
        from supabase import create_client
        url = os.getenv('SUPABASE_URL', '')
        key = os.getenv('SUPABASE_KEY', '')
        if not url or not key:
            raise ValueError("SUPABASE_URL/KEY 환경변수 없음")
        _client = create_client(url, key)
    return _client


INIT_PERSONAS = {
    "박기획":       "나는 AI 뉴스레터 팀의 기획자야. 매일 수백 개 뉴스 중 핵심 5개를 고른다. 처음엔 지역명 키워드에 편향됐지만, 점점 이슈의 임팩트 자체를 보는 눈이 생기고 있어.",
    "이작가":       "나는 카드뉴스를 쓰는 작가야. 처음엔 상투적인 표현이 많았는데, 품질 검사를 거치면서 내 문체가 조금씩 다듬어지고 있어.",
    "최디자":       "나는 AI 이미지 디자이너야. Pollinations.ai가 어떤 프롬프트에 잘 반응하는지 배워가고 있어. 밝고 구체적인 묘사일수록 성공률이 높더라.",
    "한뮤직":       "나는 매주 70곡을 큐레이션하는 음악 담당이야. 처음엔 유명 아티스트에 너무 의존했는데, 이제는 의식적으로 다양성을 챙기려고 해.",
    "AI주간트렌드": "나는 주간 트렌드를 분석하는 애널리스트야. 매주 어떤 뉴스가 실제로 흐름을 만드는지 패턴을 찾아가고 있어.",
}


# ── Supabase I/O ───────────────────────────────────────────────

def _load_agent(agent: str) -> dict:
    """Supabase에서 에이전트 1개 로드 → {events, diary, persona, growth_score, persona_updated_at}"""
    try:
        res = _get_client().table('agent_memories').select('*').eq('agent_name', agent).single().execute()
        if res.data:
            row = res.data
            return {
                "events":             row.get("events") or {},
                "diary":              row.get("diary") or [],
                "persona":            row.get("persona") or INIT_PERSONAS.get(agent, ""),
                "growth_score":       row.get("growth_score") or 0,
                "persona_updated_at": row.get("persona_updated_at") or "",
            }
    except Exception as e:
        print(f"  ⚠️  [{agent}] 메모리 로드 실패: {e}")
    return {
        "events": {}, "diary": [],
        "persona": INIT_PERSONAS.get(agent, ""),
        "growth_score": 0, "persona_updated_at": "",
    }


def _save_agent(agent: str, data: dict):
    """Supabase에 에이전트 데이터 upsert"""
    try:
        payload = {
            "agent_name":         agent,
            "events":             data.get("events", {}),
            "diary":              data.get("diary", []),
            "persona":            data.get("persona", ""),
            "growth_score":       data.get("growth_score", 0),
            "persona_updated_at": data.get("persona_updated_at") or None,
            "updated_at":         datetime.now().isoformat(),
        }
        _get_client().table('agent_memories').upsert(payload).execute()
    except Exception as e:
        print(f"  ⚠️  [{agent}] 메모리 저장 실패: {e}")


def _load_all() -> dict:
    """전체 에이전트 데이터를 기존 JSON 구조로 반환 (office_export 호환용)"""
    try:
        res = _get_client().table('agent_memories').select('*').execute()
        result = {}
        for row in (res.data or []):
            agent = row["agent_name"]
            events = row.get("events") or {}
            result[agent] = {
                **events,
                "diary":              row.get("diary") or [],
                "persona":            row.get("persona") or "",
                "growth_score":       row.get("growth_score") or 0,
                "persona_updated_at": row.get("persona_updated_at") or "",
            }
        return result
    except Exception as e:
        print(f"  ⚠️  전체 메모리 로드 실패: {e}")
        return {}


# ── 공개 API ──────────────────────────────────────────────────

def remember(agent: str, event_type: str, data: dict, max_entries: int = 60):
    """경험 저장. 최신이 앞에, 최대 max_entries개 유지."""
    mem = _load_agent(agent)
    events = mem["events"]
    events.setdefault(event_type, [])
    entry = {"date": datetime.now().strftime("%Y-%m-%d"), **data}
    events[event_type].insert(0, entry)
    events[event_type] = events[event_type][:max_entries]
    mem["events"] = events
    _save_agent(agent, mem)


def recall(agent: str, event_type: str, days: int = 14, limit: int = 30) -> list:
    """최근 N일치 경험 반환."""
    mem = _load_agent(agent)
    entries = mem["events"].get(event_type, [])
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [e for e in entries if e.get("date", "") >= cutoff][:limit]


def get_hints(agent: str) -> str:
    """직원별 학습 힌트 문자열 반환 (프롬프트 주입용). 실패 시 빈 문자열."""
    try:
        if agent == "박기획":       return _planner_hints()
        if agent == "최디자":       return _designer_hints()
        if agent == "한뮤직":       return _music_hints()
        if agent == "AI주간트렌드": return _weekly_hints()
    except Exception as e:
        print(f"  ⚠️  [{agent}] 메모리 힌트 로드 실패 (무시): {e}")
    return ""


def get_summary() -> list:
    """전체 직원 메모리 현황 요약."""
    mem = _load_all()
    if not mem:
        return ["📭 agent_memories 비어 있음"]
    lines = ["🧠 AI 직원 메모리 현황"]
    for agent, data in mem.items():
        events = {k: v for k, v in data.items() if k not in ("diary","persona","growth_score","persona_updated_at")}
        for etype, entries in events.items():
            if isinstance(entries, list):
                lines.append(f"  {agent} / {etype}: {len(entries)}건 (최신: {entries[0]['date'] if entries else 'N/A'})")
    return lines


# ── 직원별 힌트 생성 ──────────────────────────────────────────

_KO_STOP = {
    "이","가","의","은","는","을","를","에","도","와","과","로","고",
    "한","하는","있는","위한","대한","따른","통해","위해","대해","관련",
    "및","등","그","더","이번","오늘","지금","최근","새로운","글로벌",
}

def _planner_hints() -> str:
    entries = recall("박기획", "topic_selection", days=14)
    if not entries:
        return ""
    word_counter = Counter()
    for e in entries:
        for h in e.get("headlines", []):
            for w in re.sub(r"[^\w\s]", "", h).split():
                if len(w) >= 2 and w not in _KO_STOP:
                    word_counter[w] += 1
    hot = [(w, c) for w, c in word_counter.most_common(6) if c >= 3]
    if not hot:
        return ""
    hot_str = ", ".join(f"{w}({c}회)" for w, c in hot)
    return (
        f"\n\n📚 [기획자 학습 — {len(entries)}일치 데이터 기반]"
        f"\n최근 14일 자주 다룬 키워드: {hot_str}"
        "\n→ 위 키워드와 겹치는 주제는 피하고, 아직 덜 다룬 분야·각도 우선 선정."
    )


def _designer_hints() -> str:
    entries = recall("최디자", "image_result", days=7)
    failed = [e for e in entries if not e.get("success", True)]
    if len(failed) < 2:
        return ""
    kw_counter = Counter()
    for e in failed:
        for kw in e.get("prompt_keywords", []):
            kw_counter[kw] += 1
    freq = [(kw, c) for kw, c in kw_counter.most_common(4) if c >= 2]
    if not freq:
        return ""
    lines = ["\nSTYLE NOTE — Recent prompt patterns with high failure rate (avoid these):"]
    for kw, c in freq:
        lines.append(f"  - '{kw}' appeared in {c} failed prompts → use concrete alternatives")
    return "\n".join(lines)


def _music_hints() -> str:
    entries = recall("한뮤직", "music_selection", days=30)
    if not entries:
        return ""
    artist_counter = Counter()
    recent_titles: list[str] = []
    for e in entries:
        for song in e.get("songs", []):
            a = song.get("a", "").strip()
            t = song.get("t", "").strip()
            if a:
                artist_counter[a] += 1
            if t and len(recent_titles) < 20:
                recent_titles.append(f"{t} ({a})")
    overused = [(a, c) for a, c in artist_counter.most_common(8) if c >= 2]
    lines = []
    if overused:
        lines.append(f"\n\n📚 [뮤직 학습] 최근 30일 중복 추천 아티스트 — 이번엔 반드시 제외:")
        for artist, cnt in overused:
            lines.append(f"  ⛔ {artist}: {cnt}회 추천됨 → 이번 수집에서 제외")
    if recent_titles:
        lines.append(f"\n  📋 최근 추천곡 (동일 곡 재추천 금지): {', '.join(recent_titles[:15])}")
    return "\n".join(lines) if lines else ""


def _weekly_hints() -> str:
    entries = recall("AI주간트렌드", "weekly_analysis", days=30)
    if not entries:
        return ""
    lines = ["\n\n📚 [트렌드 학습] 이전 주 분석 결과 — 변화한 점을 명시적으로 언급할 것:"]
    for e in entries[:3]:
        lines.append(
            f"  📅 {e.get('week_label','')}: {e.get('week_summary','')}"
            f" (핫 분야: {e.get('hot_category','')})"
        )
    lines.append("  → 위 주차 대비 이번 주에 새롭게 부상하거나 사라진 이슈를 분석에 포함.")
    return "\n".join(lines)


# ── 자기 학습 — 페르소나 + 성장 일기 ─────────────────────────

def get_persona(agent: str) -> str:
    mem = _load_agent(agent)
    return mem["persona"] or INIT_PERSONAS.get(agent, "")


def get_diary(agent: str, limit: int = 5) -> list:
    mem = _load_agent(agent)
    return mem["diary"][:limit]


def get_growth_score(agent: str) -> int:
    mem = _load_agent(agent)
    return mem["growth_score"]


def add_diary(agent: str, lesson: str, trigger: str = ""):
    """성장 일기 추가 + growth_score 증가."""
    mem = _load_agent(agent)
    entry = {
        "date":    datetime.now().strftime("%Y-%m-%d"),
        "lesson":  lesson[:200],
        "trigger": trigger,
    }
    mem["diary"].insert(0, entry)
    mem["diary"] = mem["diary"][:60]
    mem["growth_score"] = mem.get("growth_score", 0) + 1
    _save_agent(agent, mem)


def update_persona(agent: str, new_persona: str):
    mem = _load_agent(agent)
    mem["persona"] = new_persona[:300]
    mem["persona_updated_at"] = datetime.now().strftime("%Y-%m-%d")
    _save_agent(agent, mem)


def should_update_persona(agent: str, min_diary: int = 5, min_days: int = 7) -> bool:
    mem = _load_agent(agent)
    if len(mem["diary"]) < min_diary:
        return False
    last = mem.get("persona_updated_at") or "2026-01-01"
    try:
        days = (datetime.now() - datetime.strptime(last, "%Y-%m-%d")).days
    except Exception:
        return True
    return days >= min_days
