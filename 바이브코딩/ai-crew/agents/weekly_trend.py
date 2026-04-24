"""
📊 주간 트렌드 브리핑 에이전트 (매주 월요일 실행)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
지난 7일 docs/content/YYYY-MM-DD.json 분석
→ 분야별 이슈 빈도 집계 + Gemini 인사이트
→ docs/weekly_trend.json 저장 → GitHub Pages 자동 반영
"""

import os, json, subprocess
from datetime import date, timedelta
from utils.gemini_client import ask_gemini
from utils.agent_memory import remember, get_hints

DOCS_CONTENT_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "content")
WEEKLY_TREND_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "weekly_trend.json")

SYSTEM = """당신은 30년 경력의 수석 뉴스 큐레이터입니다.
이번 주 뉴스 데이터를 분석해 독자에게 실질적인 인사이트를 제공합니다.
JSON만 출력합니다. 다른 텍스트, 마크다운 코드블록 없이 순수 JSON만."""

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
            for a in articles[:2]:
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


def _ai_analysis(agg: dict, days_analyzed: int) -> dict:
    """Gemini로 인사이트 분석 → JSON 반환"""
    weekly_hints = get_hints("AI주간트렌드")
    cat_summary = "\n".join(
        f"  {o['name']}: {o['count']}건"
        for o in agg["category_counts"]
    )
    headlines_text = "\n".join(f"  - {h}" for h in agg["all_headlines"][:35])
    blogs_text     = "\n".join(f"  - {b}" for b in agg["blog_topics"][:7])

    # 카테고리별 기사 샘플
    samples_text = ""
    for cat, titles in agg["news_samples"].items():
        if titles:
            samples_text += f"\n  [{cat}]\n" + "\n".join(f"    · {t}" for t in titles[:4])

    prompt = f"""아래는 지난 {days_analyzed}일간 AI 뉴스레터의 뉴스 데이터입니다.{weekly_hints}

=== 분야별 기사 건수 ===
{cat_summary}

=== 이번 주 카드뉴스 헤드라인 (AI 선정) ===
{headlines_text}

=== 이번 주 블로그 주제 ===
{blogs_text}

=== 분야별 기사 샘플 ===
{samples_text}

위 데이터를 분석해서 아래 JSON 형식으로 출력하세요.
수치·이름은 위 데이터에 있는 것만 사용. 없는 내용 창작 금지.

{{
  "week_summary": "이번 주 전체를 한 문장으로 — 핵심 키워드 2~3개 포함 (30자 내외)",
  "hot_category": "가장 뉴스가 많았던 분야명 (위 분야명 그대로)",
  "sections": [
    {{
      "category": "분야명 (위 분야명 그대로)",
      "top_issue": "이번 주 이 분야 핵심 이슈 (20자 내외)",
      "insight": "2~3문장. 구체적 기업명·수치 포함. 왜 중요한지 + 앞으로 어떻게 될지."
    }}
  ],
  "weekly_insight": "이번 주를 관통하는 큰 흐름 4~5문장. 분야 간 연결고리, 투자자·직장인 관점의 실질적 시사점 포함.",
  "next_watch": [
    "다음 주 주목할 이슈나 일정 3~4개 (bullet 형식, 위 뉴스 흐름에서 유추)"
  ]
}}

규칙:
- sections는 기사 건수 상위 4개 분야만 (0건 분야 제외)
- weekly_insight는 반드시 200자 이상
- 한국어·영어·이모지만. 한자·일본어 등 절대 금지
- JSON만 출력. 코드블록(```) 없이."""

    raw = ask_gemini(prompt, system=SYSTEM, temperature=0.65, json_mode=True, max_tokens=2000)
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except Exception:
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise ValueError(f"JSON 파싱 실패: {raw[:200]}")


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
