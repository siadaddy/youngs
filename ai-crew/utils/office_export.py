"""
AI 사무실 학습 기록 export — ai-crew 측
agent_memory.json → docs/office_memory.json 에 4명 에이전트 학습 기록 병합 저장
"""
import os, json, re
from datetime import datetime
from collections import Counter

REPO_ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OFFICE_FILE   = os.path.join(REPO_ROOT, "docs", "office_memory.json")
MEM_FILE      = os.path.join(os.path.dirname(__file__), "..", "agent_memory.json")
WEEKLY_FILE   = os.path.join(REPO_ROOT, "docs", "weekly_trend.json")


def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_diary(mem, agent_name):
    """성장 일기 최근 3건 + 페르소나 + 성장점수 로드"""
    agent_data = mem.get(agent_name, {})
    diary      = agent_data.get("diary", [])[:3]
    persona    = agent_data.get("persona", "")
    score      = agent_data.get("growth_score", 0)
    return diary, persona[:60] if persona else "", score


def _planner(mem):
    entries = mem.get("박기획", {}).get("topic_selection", [])
    topics, kw_cnt = [], Counter()
    for e in entries[:14]:
        for h in e.get("headlines", []):
            if h:
                topics.append(h[:28])
                for w in re.sub(r'[^\w\s]', '', h).split():
                    if len(w) > 1:
                        kw_cnt[w] += 1

    repeat_kw = [f"'{k}'({v}회)" for k, v in kw_cnt.most_common(3) if v >= 2]
    hint = f"⚠️ 반복 키워드: {', '.join(repeat_kw)} — 새 각도 필요" if repeat_kw else "✅ 다양한 주제 선정 중"
    last_active = entries[0]["date"] if entries else ""
    diary, persona, score = _load_diary(mem, "박기획")
    return {"hint": hint, "recent_topics": topics[:4], "last_active": last_active,
            "diary": diary, "persona": persona, "growth_score": score}


def _designer(mem):
    entries = mem.get("최디자", {}).get("image_result", [])
    total   = len(entries)
    success = sum(1 for e in entries if e.get("success"))
    fail_kw = Counter()
    for e in entries:
        if not e.get("success"):
            for k in e.get("prompt_keywords", []):
                fail_kw[k] += 1
    rate    = round(success / total * 100) if total > 0 else 0
    bad_kw  = [f"'{k}'({v}회)" for k, v in fail_kw.most_common(2) if v >= 2]
    hint    = f"⚠️ 실패 키워드: {', '.join(bad_kw)}" if bad_kw else f"✅ 이미지 성공률 {rate}%"
    last_active = entries[0]["date"] if entries else ""
    diary, persona, score = _load_diary(mem, "최디자")
    return {"hint": hint, "success_rate": rate, "last_active": last_active,
            "diary": diary, "persona": persona, "growth_score": score}


def _music(mem):
    entries     = mem.get("한뮤직", {}).get("music_selection", [])
    artist_cnt  = Counter()
    for e in entries[:12]:
        for s in e.get("songs", []):
            a = s.get("a", "")
            if a:
                artist_cnt[a] += 1
    overused    = [f"{a}({c}회)" for a, c in artist_cnt.most_common(3) if c >= 2]
    hint        = f"⚠️ {', '.join(overused[:2])} 반복 — 다양화 필요" if overused else "✅ 아티스트 다양성 양호"
    last_active = entries[0]["date"] if entries else ""
    diary, persona, score = _load_diary(mem, "한뮤직")
    return {"hint": hint, "overused": overused[:3], "last_active": last_active,
            "diary": diary, "persona": persona, "growth_score": score}


def _weekly(mem):
    entries = mem.get("AI주간트렌드", {}).get("weekly_analysis", [])
    diary, persona, score = _load_diary(mem, "AI주간트렌드")
    if entries:
        last = entries[0]
        return {
            "hint":         f"📊 {last.get('week_summary','')}",
            "last_summary": last.get("week_summary", ""),
            "hot":          last.get("hot_category", ""),
            "last_active":  last.get("date", ""),
            "diary": diary, "persona": persona, "growth_score": score,
        }
    # 메모리 없으면 weekly_trend.json 직접 참조
    wt = _load(WEEKLY_FILE)
    if wt.get("week_summary"):
        return {
            "hint":         f"📊 {wt.get('week_summary','')}",
            "last_summary": wt.get("week_summary", ""),
            "hot":          wt.get("hot_category", ""),
            "last_active":  wt.get("generated_at", ""),
            "diary": diary, "persona": persona, "growth_score": score,
        }
    return {"hint": "📊 주간 분석 대기 중", "last_active": "",
            "diary": diary, "persona": persona, "growth_score": score}


def _crew_log(mem):
    log = []

    for e in mem.get("박기획", {}).get("topic_selection", [])[:6]:
        topics = e.get("headlines", [])
        if topics:
            log.append({
                "time":  e.get("date", ""),
                "agent": "박기획", "icon": "📋",
                "msg":   f"카드뉴스 주제 확정: {topics[0][:22]}",
                "type":  "plan",
            })

    for e in mem.get("최디자", {}).get("image_result", [])[:6]:
        success  = e.get("success", True)
        headline = e.get("headline", "")[:22]
        log.append({
            "time":  e.get("date", ""),
            "agent": "최디자", "icon": "🎨",
            "msg":   f"{'✅' if success else '❌'} {headline} 이미지 {'성공' if success else '실패'}",
            "type":  "design",
        })

    for e in mem.get("한뮤직", {}).get("music_selection", [])[:4]:
        cnt = len(e.get("songs", []))
        log.append({
            "time":  e.get("date", ""),
            "agent": "한뮤직", "icon": "🎵",
            "msg":   f"플레이리스트 {cnt}곡 큐레이션 완료",
            "type":  "music",
        })

    for e in mem.get("AI주간트렌드", {}).get("weekly_analysis", [])[:3]:
        log.append({
            "time":  e.get("date", ""),
            "agent": "AI주간트렌드", "icon": "📊",
            "msg":   f"주간 트렌드: {e.get('week_summary','')[:30]}",
            "type":  "trend",
        })

    # 성장 일기 항목 (4명 통합)
    for agent_name, icon in [("박기획","📋"),("최디자","🎨"),("한뮤직","🎵"),("AI주간트렌드","📊")]:
        for e in mem.get(agent_name, {}).get("diary", [])[:3]:
            log.append({
                "time":  e.get("date", ""),
                "agent": agent_name, "icon": icon,
                "msg":   f"📖 {e.get('lesson','')[:35]}",
                "type":  "diary",
            })

    log.sort(key=lambda x: x.get("time", ""), reverse=True)
    return log[:30]


def export():
    """office_memory.json에 ai-crew 에이전트 데이터 병합 저장"""
    mem      = _load(MEM_FILE)
    existing = _load(OFFICE_FILE) if os.path.exists(OFFICE_FILE) else {}
    agents   = existing.get("agents", {})

    agents["박기획"]       = _planner(mem)
    agents["최디자"]       = _designer(mem)
    agents["한뮤직"]       = _music(mem)
    agents["AI주간트렌드"] = _weekly(mem)

    crew_log    = _crew_log(mem)
    advisor_log = [e for e in existing.get("log", []) if e.get("agent") == "AI어드바이저"]
    all_log     = crew_log + advisor_log
    all_log.sort(key=lambda x: x.get("time", ""), reverse=True)

    out = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "agents":  agents,
        "log":     all_log[:50],
    }
    with open(OFFICE_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
