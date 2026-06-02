"""
🧠 AI 직원 공통 메모리 시스템
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
매 실행마다 경험을 agent_memory.json에 누적.
각 직원이 과거 경험을 바탕으로 프롬프트를 자동 조정함.

사용법:
    from utils.agent_memory import remember, recall, get_hints
    remember("박기획", "topic_selection", {"headlines": [...], "blog_title": "..."})
    hints = get_hints("박기획")   # 프롬프트에 주입
"""

import os, json, re
from datetime import datetime, timedelta
from collections import Counter

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "agent_memory.json")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rlaemixsrmhocxjhkjxl.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


# ── 기본 I/O ──────────────────────────────────────────────────

def _load_from_supabase() -> dict:
    """로컬 파일 없을 때 Supabase에서 에이전트 메모리 복원 (GitHub Actions용)."""
    try:
        import requests as _req, ast as _ast
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        res = _req.get(
            f"{SUPABASE_URL}/rest/v1/agent_memories?select=*",
            headers=headers,
            timeout=5,
        )
        if res.status_code != 200:
            return {}
        rows = res.json()
        if not rows:
            return {}

        result = {}
        for row in rows:
            agent = row.get("agent_name", "")
            if not agent:
                continue
            mem: dict = {}
            # events 필드 (TEXT 또는 JSONB)
            ev = row.get("events")
            if isinstance(ev, dict):
                mem.update(ev)
            elif isinstance(ev, str) and ev.strip():
                try:
                    mem.update(json.loads(ev))
                except Exception:
                    try:
                        mem.update(_ast.literal_eval(ev))
                    except Exception:
                        pass
            # diary 필드
            d = row.get("diary")
            if isinstance(d, list):
                mem["diary"] = d
            elif isinstance(d, str) and d.strip():
                try:
                    mem["diary"] = json.loads(d)
                except Exception:
                    try:
                        mem["diary"] = _ast.literal_eval(d)
                    except Exception:
                        pass
            if row.get("persona"):
                mem["persona"] = row["persona"]
            if row.get("growth_score") is not None:
                mem["growth_score"] = row["growth_score"]
            if row.get("persona_updated_at"):
                mem["persona_updated_at"] = row["persona_updated_at"]
            result[agent] = mem

        if result:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  🔄 Supabase에서 {len(result)}개 에이전트 메모리 복원 완료")
        return result
    except Exception as e:
        print(f"  ⚠️  Supabase 메모리 로드 실패: {e}")
    return {}


def _load() -> dict:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data:
                return data
        except Exception:
            pass
    return _load_from_supabase()


def _sync_supabase(data: dict):
    """agent_memories 테이블에 에이전트별 upsert (실패해도 로컬 저장 완료됨)"""
    try:
        import requests as _req
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
        _SKIP = {"persona", "diary", "growth_score", "persona_updated_at"}
        for agent_name, mem in data.items():
            events = {k: v for k, v in mem.items() if k not in _SKIP}
            _req.post(
                f"{SUPABASE_URL}/rest/v1/agent_memories",
                headers=headers,
                json={
                    "agent_name":        agent_name,
                    "events":            events,
                    "diary":             mem.get("diary", []),
                    "persona":           mem.get("persona", ""),
                    "growth_score":      mem.get("growth_score", 0),
                    "persona_updated_at": mem.get("persona_updated_at") or None,
                    "updated_at":        datetime.now().isoformat(),
                },
                timeout=5,
            )
    except Exception:
        pass


def _save(data: dict):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _sync_supabase(data)


# ── 공개 API ──────────────────────────────────────────────────

def remember(agent: str, event_type: str, data: dict, max_entries: int = 60):
    """경험 저장. 최신이 앞에, 최대 max_entries개 유지."""
    mem = _load()
    mem.setdefault(agent, {}).setdefault(event_type, [])
    entry = {"date": datetime.now().strftime("%Y-%m-%d"), **data}
    mem[agent][event_type].insert(0, entry)
    mem[agent][event_type] = mem[agent][event_type][:max_entries]
    _save(mem)


def recall(agent: str, event_type: str, days: int = 14, limit: int = 30) -> list:
    """최근 N일치 경험 반환."""
    mem = _load()
    entries = mem.get(agent, {}).get(event_type, [])
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [e for e in entries if e.get("date", "") >= cutoff][:limit]


def get_hints(agent: str) -> str:
    """직원별 학습 힌트 문자열 반환 (프롬프트 주입용). 실패 시 빈 문자열."""
    try:
        if agent == "박기획":       return _planner_hints()
        if agent == "이작가":       return _writer_hints()
        if agent == "최디자":       return _designer_hints()
        if agent == "한뮤직":       return _music_hints()
        if agent == "AI주간트렌드": return _weekly_hints()
    except Exception as e:
        print(f"  ⚠️  [{agent}] 메모리 힌트 로드 실패 (무시): {e}")
    return ""


def get_summary() -> list:
    """전체 직원 메모리 현황 요약 (CLI 확인용)."""
    mem = _load()
    if not mem:
        return ["📭 agent_memory.json 비어 있음"]
    lines = ["🧠 AI 직원 메모리 현황"]
    for agent, events in mem.items():
        for etype, entries in events.items():
            lines.append(f"  {agent} / {etype}: {len(entries)}건 (최신: {entries[0]['date'] if entries else 'N/A'})")
    return lines


# ── 직원별 힌트 생성 ──────────────────────────────────────────

_KO_STOP = {
    "이","가","의","은","는","을","를","에","도","와","과","로","고",
    "한","하는","있는","위한","대한","따른","통해","위해","대해","관련",
    "및","등","그","더","이번","오늘","지금","최근","새로운","글로벌",
}

def _planner_hints() -> str:
    mem = _load()
    persona = mem.get("박기획", {}).get("persona", "")
    entries = recall("박기획", "topic_selection", days=14)

    word_counter = Counter()
    for e in entries:
        for h in e.get("headlines", []):
            for w in re.sub(r"[^\w\s]", "", h).split():
                if len(w) >= 2 and w not in _KO_STOP:
                    word_counter[w] += 1

    hot = [(w, c) for w, c in word_counter.most_common(6) if c >= 3]

    parts = []
    if persona:
        parts.append(f"\n\n🎭 [박기획 현재 관점]\n{persona}\n→ 이 관점을 바탕으로 오늘 뉴스의 각도를 잡아라.")
    if hot and entries:
        hot_str = ", ".join(f"{w}({c}회)" for w, c in hot)
        parts.append(
            f"\n\n📚 [기획자 학습 — {len(entries)}일치 데이터 기반]"
            f"\n최근 14일 자주 다룬 키워드: {hot_str}"
            "\n→ 위 키워드와 겹치는 주제는 피하고, 아직 덜 다룬 분야·각도 우선 선정."
        )
    return "".join(parts)


def _designer_hints() -> str:
    mem = _load()
    persona = mem.get("최디자", {}).get("persona", "")
    entries = recall("최디자", "image_result", days=7)
    failed = [e for e in entries if not e.get("success", True)]

    parts = []
    if persona:
        parts.append(f"\nDESIGNER INSIGHT: {persona}")

    if len(failed) >= 2:
        kw_counter = Counter()
        for e in failed:
            for kw in e.get("prompt_keywords", []):
                kw_counter[kw] += 1
        freq = [(kw, c) for kw, c in kw_counter.most_common(4) if c >= 2]
        if freq:
            parts.append("\nSTYLE NOTE — Recent prompt patterns with high failure rate (avoid these):")
            for kw, c in freq:
                parts.append(f"  - '{kw}' appeared in {c} failed prompts → use concrete alternatives")

    return "\n".join(parts)


def _writer_hints() -> str:
    mem = _load()
    persona = mem.get("이작가", {}).get("persona", "")
    diary = mem.get("이작가", {}).get("diary", [])
    if not persona and not diary:
        return ""

    parts = []
    if persona:
        parts.append(f"\n\n✍️ [이작가 현재 문체 원칙]\n{persona}\n→ 이 관점을 글쓰기 스타일에 반영해라.")
    if diary:
        recent_lessons = [e["lesson"][:40] for e in diary[:3] if e.get("lesson")]
        if recent_lessons:
            parts.append("\n최근 학습: " + " / ".join(recent_lessons))
    return "".join(parts)


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

INIT_PERSONAS = {
    "박기획": "나는 AI 뉴스레터 팀의 기획자야. 매일 수백 개 뉴스 중 핵심 5개를 고른다. 처음엔 지역명 키워드에 편향됐지만, 점점 이슈의 임팩트 자체를 보는 눈이 생기고 있어.",
    "이작가": "나는 카드뉴스를 쓰는 작가야. 처음엔 상투적인 표현이 많았는데, 품질 검사를 거치면서 내 문체가 조금씩 다듬어지고 있어.",
    "최디자": "나는 AI 이미지 디자이너야. Pollinations.ai가 어떤 프롬프트에 잘 반응하는지 배워가고 있어. 밝고 구체적인 묘사일수록 성공률이 높더라.",
    "한뮤직": "나는 매주 70곡을 큐레이션하는 음악 담당이야. 처음엔 유명 아티스트에 너무 의존했는데, 이제는 의식적으로 다양성을 챙기려고 해.",
    "AI주간트렌드": "나는 주간 트렌드를 분석하는 애널리스트야. 매주 어떤 뉴스가 실제로 흐름을 만드는지 패턴을 찾아가고 있어.",
}


def get_persona(agent: str) -> str:
    """현재 페르소나 반환. 없으면 초기값."""
    mem = _load()
    return mem.get(agent, {}).get("persona", INIT_PERSONAS.get(agent, ""))


def get_diary(agent: str, limit: int = 5) -> list:
    """최근 성장 일기 반환."""
    mem = _load()
    return mem.get(agent, {}).get("diary", [])[:limit]


def get_growth_score(agent: str) -> int:
    mem = _load()
    return mem.get(agent, {}).get("growth_score", 0)


def add_diary(agent: str, lesson: str, trigger: str = ""):
    """성장 일기 추가 + growth_score 증가."""
    mem = _load()
    mem.setdefault(agent, {})
    mem[agent].setdefault("diary", [])
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "lesson": lesson[:200],
        "trigger": trigger,
    }
    mem[agent]["diary"].insert(0, entry)
    mem[agent]["diary"] = mem[agent]["diary"][:60]
    mem[agent]["growth_score"] = mem[agent].get("growth_score", 0) + 1
    _save(mem)


def update_persona(agent: str, new_persona: str):
    """AI가 스스로 페르소나를 업데이트."""
    mem = _load()
    mem.setdefault(agent, {})
    mem[agent]["persona"] = new_persona[:300]
    mem[agent]["persona_updated_at"] = datetime.now().strftime("%Y-%m-%d")
    _save(mem)


def should_update_persona(agent: str, min_diary: int = 5, min_days: int = 7) -> bool:
    """페르소나 재작성 시점 여부 (일기 5개 이상 + 7일 이상 경과)."""
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
