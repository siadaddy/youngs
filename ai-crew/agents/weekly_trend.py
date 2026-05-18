"""
📊 주간 트렌드 브리핑 에이전트 (매주 월요일 실행)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
지난 7일 docs/content/YYYY-MM-DD.json 분석
→ 분야별 이슈 빈도 집계 + Gemini 인사이트
→ docs/weekly_trend.json 저장 → GitHub Pages 자동 반영
"""

import os, json, subprocess
from datetime import date, timedelta
from utils.gemini_client import ask_ai
from utils.agent_memory import remember, get_hints, add_diary

DOCS_CONTENT_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "content")
WEEKLY_TREND_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "weekly_trend.json")

SYSTEM = """당신은 BMW 딜러십에 근무하는 30대 직장인을 위한 경제·기술 뉴스 큐레이터입니다.
이번 주 뉴스를 날카롭게 분석해 "그래서 나한테 뭔 의미야?"에 바로 답하는 인사이트를 씁니다.

글쓰기 원칙:
- 구체적 기업명·수치·날짜가 없는 문장은 쓰지 않는다
- "~이다", "~기 때문이다", "~것으로 예상된다" 패턴 3회 이상 반복 금지
- "중요성이 증가", "새로운 산업 창출", "많은 기업들" 같은 공허한 표현 금지
- 딱 이 뉴스를 읽은 독자가 내일 동료에게 꺼낼 수 있는 얘기를 써라
- JSON만 출력. 코드블록(```) 없이."""

# 표시할 카테고리 순서 (하이라이트·BMW는 집계에서 제외)
_CAT_ORDER = [
    "🤖 AI / 인공지능",
    "💰 경제 / 금융",
    "💻 기술 / IT",
    "🚗 자동차",
    "🏙️ 사회",
    "🚨 사건 / 사고",
]


def _load_recent_days(n: int = 7) -> list[dict]:
    """최근 n일치 content JSON 로드. 파일 없는 날은 스킵."""
    today = date.today()
    result = []
    for i in range(1, n + 1):  # 어제부터 n일 전까지
        d = today - timedelta(days=i)
        path = os.path.join(DOCS_CONTENT_DIR, f"{d.strftime('%Y-%m-%d')}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    result.append(json.load(f))
            except Exception:
                pass
    return result


def _aggregate(days_data: list[dict]) -> dict:
    """7일치 데이터 집계: 카테고리 건수, 헤드라인, 블로그 주제"""
    cat_counts: dict[str, int] = {}
    all_headlines: list[str] = []
    blog_topics: list[str] = []
    news_samples: dict[str, list[str]] = {}  # 카테고리별 기사 제목 샘플

    for day in days_data:
        # 카드 헤드라인
        for c in day.get("captions", []):
            h = c.get("headline", "").strip()
            if h:
                all_headlines.append(h)

        # 블로그 주제
        bt = day.get("blog_title", "").strip()
        if bt:
            blog_topics.append(bt)

        # 카테고리별 기사 수
        for cat, articles in day.get("news", {}).items():
            if "하이라이트" in cat or "BMW" in cat:
                continue
            cat_counts[cat] = cat_counts.get(cat, 0) + len(articles)
            if cat not in news_samples:
                news_samples[cat] = []
            for a in articles[:5]:
                title = a.get("title", "").strip()
                if title and title not in news_samples[cat]:
                    news_samples[cat].append(title)

    # 카테고리 정렬 (정해진 순서 + 나머지)
    ordered = []
    for cat in _CAT_ORDER:
        if cat in cat_counts:
            ordered.append({"name": cat, "count": cat_counts[cat]})
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        if not any(o["name"] == cat for o in ordered):
            ordered.append({"name": cat, "count": cnt})

    # 최대값 기준 백분율 계산 (바 차트용)
    max_cnt = max((o["count"] for o in ordered), default=1)
    for o in ordered:
        o["pct"] = round(o["count"] / max_cnt * 100)

    return {
        "category_counts": ordered,
        "all_headlines":   all_headlines,
        "blog_topics":     blog_topics,
        "news_samples":    news_samples,
    }


def _close_json(s: str) -> str:
    """잘린 JSON 문자열을 괄호/따옴표 균형을 맞춰 닫는다."""
    in_str, escaped = False, False
    for ch in s:
        if escaped:
            escaped = False
            continue
        if ch == '\\' and in_str:
            escaped = True
            continue
        if ch == '"':
            in_str = not in_str
    if in_str:
        s += '"'
    opens = s.count('{') - s.count('}')
    arr_opens = s.count('[') - s.count(']')
    s += ']' * max(arr_opens, 0)
    s += '}' * max(opens, 0)
    return s


def _ai_analysis(agg: dict, days_analyzed: int) -> dict:
    """Gemini로 인사이트 분석 → JSON 반환"""
    weekly_hints = get_hints("AI주간트렌드")
    cat_summary = "\n".join(
        f"  {o['name']}: {o['count']}건"
        for o in agg["category_counts"]
    )
    headlines_text = "\n".join(f"  - {h}" for h in agg["all_headlines"][:20])
    blogs_text     = "\n".join(f"  - {b}" for b in agg["blog_topics"][:5])

    # 카테고리별 기사 샘플 (상위 4개 카테고리만)
    top_cats = [o["name"] for o in agg["category_counts"][:4]]
    samples_text = ""
    for cat in top_cats:
        titles = agg["news_samples"].get(cat, [])
        if titles:
            samples_text += f"\n  [{cat}]\n" + "\n".join(f"    · {t}" for t in titles[:3])

    prompt = f"""아래는 지난 {days_analyzed}일간 AI 뉴스레터의 뉴스 데이터입니다.{weekly_hints}

=== 분야별 기사 건수 ===
{cat_summary}

=== 이번 주 카드뉴스 헤드라인 (AI 선정) ===
{headlines_text}

=== 이번 주 블로그 주제 ===
{blogs_text}

=== 분야별 기사 샘플 (실제 뉴스 제목) ===
{samples_text}

위 데이터만 근거로 아래 JSON 형식으로 출력하세요.
데이터에 없는 수치·기업명·사건 절대 창작 금지.

{{
  "week_summary": "이번 주 전체를 한 문장으로 — 위 헤드라인에서 뽑은 핵심 키워드 2~3개 포함 (30자 내외)",
  "hot_category": "기사 건수 1위 분야명 (위 분야명 그대로 복사)",
  "sections": [
    {{
      "category": "분야명 (위 분야명 그대로 복사 — 절대 바꾸지 말 것)",
      "top_issue": "위 기사 제목에서 뽑은 이번 주 핵심 이슈 한 줄 (20자 내외)",
      "insight": "3문장. ①위 기사 제목에 실제로 등장한 기업명·인물명·수치 반드시 포함. ②왜 중요한지. ③앞으로 어떻게 될지."
    }}
  ],
  "weekly_insight": "이번 주 뉴스를 관통하는 큰 흐름 4~5문장. 위 헤드라인에 실제로 등장한 이슈·기업·수치 언급. 분야 간 연결고리. BMW 딜러 직장인 관점의 실질적 시사점.",
  "next_watch": [
    "위 뉴스 흐름에서 실제로 유추한 다음 주 주목 이슈 (막연한 '동향 주목' 금지 — 구체적 기업명·이벤트·날짜 포함)"
  ]
}}

⚠️ 반드시 지킬 규칙:
- sections: 기사 건수 상위 4개 분야만 포함 (0건 분야 제외)
- weekly_insight: 반드시 250자 이상
- next_watch: 3~4개, 각 항목에 구체적 기업명 또는 이벤트명 포함
- 한국어·영어·이모지만. 베트남어·러시아어·한자·일본어 등 절대 금지
- JSON만 출력. 코드블록(```) 없이."""

    raw = ask_ai(prompt, system=SYSTEM, temperature=0.55, json_mode=False, max_tokens=4096)
    import re as _re
    raw = raw.replace("```json", "").replace("```", "").strip()
    raw = _re.sub(r'[Ѐ-ӿĀ-ɏḀ-ỿ]', '', raw)

    try:
        return json.loads(raw)
    except Exception:
        # 잘린 JSON 복구: { ... } 추출 후 잘린 부분 닫기
        m = _re.search(r'\{.*', raw, _re.DOTALL)
        if m:
            fragment = m.group()
            fragment = _close_json(fragment)
            try:
                return json.loads(fragment)
            except Exception:
                pass
        raise ValueError(f"JSON 파싱 실패: {raw[:300]}")


def run():
    print("📊 주간 트렌드 브리핑 에이전트 실행 중...")

    days_data = _load_recent_days(7)
    if not days_data:
        print("  ⚠️  분석 가능한 콘텐츠 데이터 없음 — 스킵")
        return

    print(f"  📂 {len(days_data)}일치 데이터 집계 중...")
    agg = _aggregate(days_data)

    print(f"  🤖 Gemini 인사이트 분석 중...")
    ai = _ai_analysis(agg, len(days_data))

    # 날짜 범위 계산
    today = date.today()
    oldest = today - timedelta(days=len(days_data))
    week_label = f"{oldest.strftime('%m/%d')} ~ {(today - timedelta(days=1)).strftime('%m/%d')}"

    remember("AI주간트렌드", "weekly_analysis", {
        "week_label":   week_label,
        "week_summary": ai.get("week_summary", ""),
        "hot_category": ai.get("hot_category", ""),
    })

    hot = ai.get("hot_category", "")
    summary = ai.get("week_summary", "")
    add_diary("AI주간트렌드", f"{week_label} 주간 분석 완료. 이번 주 핫이슈는 {hot}. '{summary}'", trigger="weekly_trend")

    # 기존 history 불러오기 (최대 12주)
    history = []
    if os.path.exists(WEEKLY_TREND_FILE):
        try:
            with open(WEEKLY_TREND_FILE, "r", encoding="utf-8") as f:
                prev = json.load(f)
            history = prev.get("history", [])
            # 현재 주 기록을 history에 추가 (이전 주 데이터)
            old_entry = {k: prev.get(k) for k in ("week_label", "generated_at", "week_summary", "hot_category")}
            if old_entry.get("week_label") and old_entry["week_label"] != week_label:
                history.insert(0, old_entry)
                history = history[:12]
        except Exception:
            pass

    payload = {
        "week_label":      week_label,
        "generated_at":    today.strftime("%Y-%m-%d"),
        "days_analyzed":   len(days_data),
        "week_summary":    ai.get("week_summary", ""),
        "hot_category":    ai.get("hot_category", ""),
        "category_counts": agg["category_counts"],
        "sections":        ai.get("sections", []),
        "weekly_insight":  ai.get("weekly_insight", ""),
        "next_watch":      ai.get("next_watch", []),
        "top_headlines":   agg["all_headlines"][:35],
        "history":         history,
    }

    with open(WEEKLY_TREND_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 주간 트렌드 완료: '{payload['week_summary']}'")
    _git_push(today)
    return payload


def _git_push(today: date):
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=os.path.dirname(__file__), text=True
        ).strip()
        subprocess.run(["git", "add", "docs/weekly_trend.json"], cwd=repo_root, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"weekly: {today.strftime('%Y-%m-%d')} 주간 트렌드 브리핑"],
            cwd=repo_root, check=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
        print("  ✅ GitHub Pages 업데이트 완료")
    except Exception as e:
        print(f"  ⚠️  GitHub push 실패: {e}")
