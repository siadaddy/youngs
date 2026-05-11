"""
📊 주간 트렌드 브리핑 에이전트 (매주 월요일 실행)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Supabase news_trends 테이블에서 지난 7일 데이터 분석
→ TOP3 등장 횟수 기반 분야 집계 + Gemini 인사이트
→ docs/weekly_trend.json 저장 → GitHub Pages 자동 반영
"""

import os, json, subprocess
from datetime import date, timedelta
from utils.gemini_client import ask_ai
from utils.agent_memory import remember, get_hints, add_diary

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


def _load_from_supabase(n: int = 7) -> list[dict]:
    """Supabase news_trends 테이블에서 최근 n일치 로드"""
    try:
        from supabase import create_client
        url = os.getenv('SUPABASE_URL', '')
        key = os.getenv('SUPABASE_KEY', '')
        if not url or not key:
            raise ValueError("SUPABASE_URL/KEY 환경변수 없음")
        client = create_client(url, key)
        today = date.today()
        dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, n + 1)]
        res = client.table('news_trends').select('date,top3,category_summaries').in_('date', dates).execute()
        rows = res.data or []
        print(f"  📡 Supabase에서 {len(rows)}일치 데이터 로드")
        return rows
    except Exception as e:
        print(f"  ⚠️  Supabase 로드 실패: {e}")
        return []


def _aggregate(days_data: list[dict]) -> dict:
    """7일치 Supabase 데이터 집계: TOP3 카테고리 등장 횟수 기반"""
    cat_counts: dict[str, int] = {}
    all_headlines: list[str] = []
    news_samples: dict[str, list[str]] = {}

    for day in days_data:
        # TOP3 카테고리 등장 횟수 집계 + 헤드라인 수집
        top3 = day.get('top3') or []
        if isinstance(top3, str):
            top3 = json.loads(top3)
        for item in top3:
            cat = item.get('category', '').strip()
            title = item.get('title', '').strip()
            if cat and "하이라이트" not in cat and "BMW" not in cat:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            if title:
                all_headlines.append(title)

        # category_summaries → news_samples (AI 분석용 컨텍스트)
        summaries = day.get('category_summaries') or {}
        if isinstance(summaries, str):
            summaries = json.loads(summaries)
        for cat, summary in summaries.items():
            if "하이라이트" in cat or "BMW" in cat:
                continue
            if cat not in news_samples:
                news_samples[cat] = []
            if summary and summary not in news_samples[cat]:
                news_samples[cat].append(str(summary)[:120])

    # 카테고리 정렬 — _CAT_ORDER 키워드 부분 일치 우선, 나머지는 등장 횟수 순
    def _order_key(cat_name: str) -> int:
        for i, order_cat in enumerate(_CAT_ORDER):
            # 이모지 제거 후 핵심 키워드로 비교
            core = order_cat.split()[-1] if " " in order_cat else order_cat
            if core in cat_name or cat_name in order_cat:
                return i
        return len(_CAT_ORDER)

    ordered = sorted(
        [{"name": cat, "count": cnt} for cat, cnt in cat_counts.items()],
        key=lambda x: (_order_key(x["name"]), -x["count"])
    )

    # 최대값 기준 백분율 계산 (바 차트용)
    max_cnt = max((o["count"] for o in ordered), default=1)
    for o in ordered:
        o["pct"] = round(o["count"] / max_cnt * 100)

    return {
        "category_counts": ordered,
        "all_headlines":   all_headlines,
        "news_samples":    news_samples,
    }


def _ai_analysis(agg: dict, days_analyzed: int) -> dict:
    """Gemini로 인사이트 분석 → JSON 반환"""
    weekly_hints = get_hints("AI주간트렌드")
    cat_summary = "\n".join(
        f"  {o['name']}: {o['count']}회 TOP3 등장"
        for o in agg["category_counts"]
    )
    headlines_text = "\n".join(f"  - {h}" for h in agg["all_headlines"][:35])

    # 카테고리별 요약 샘플
    samples_text = ""
    for cat, summaries in agg["news_samples"].items():
        if summaries:
            samples_text += f"\n  [{cat}]\n" + "\n".join(f"    · {s}" for s in summaries[:3])

    prompt = f"""아래는 지난 {days_analyzed}일간 AI 뉴스레터의 뉴스 데이터입니다.{weekly_hints}

=== 분야별 TOP3 등장 횟수 (7일 누적, 최대 21회) ===
{cat_summary}

=== 이번 주 TOP3 헤드라인 ===
{headlines_text}

=== 분야별 핵심 요약 ===
{samples_text}

위 데이터를 분석해서 아래 JSON 형식으로 출력하세요.
수치·이름은 위 데이터에 있는 것만 사용. 없는 내용 창작 금지.

{{
  "week_summary": "이번 주 전체를 한 문장으로 — 핵심 키워드 2~3개 포함 (30자 내외)",
  "hot_category": "TOP3에 가장 많이 등장한 분야명 (위 분야명 그대로)",
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
- sections는 TOP3 등장 횟수 상위 4개 분야만 (0회 분야 제외)
- weekly_insight는 반드시 200자 이상
- 한국어·영어·이모지만. 한자·일본어 등 절대 금지
- JSON만 출력. 코드블록(```) 없이."""

    import re as _re
    for attempt in range(1, 4):
        raw = ask_ai(prompt, system=SYSTEM, temperature=0.65, json_mode=True, max_tokens=3000)
        raw = raw.replace("```json", "").replace("```", "").strip()
        # JSON 문자열 값 안의 리터럴 줄바꿈을 공백으로 치환 후 파싱 시도
        cleaned = raw.replace('\n', ' ').replace('\r', ' ')
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # 원본 그대로 파싱 시도
        try:
            return json.loads(raw)
        except Exception:
            m = _re.search(r'\{.*\}', cleaned, _re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    pass
            if attempt < 3:
                print(f"  ⚠️  JSON 파싱 실패 — 재시도 ({attempt}/3)...")
                continue
        raise ValueError(f"JSON 파싱 실패: {raw[:300]}")


def run():
    print("📊 주간 트렌드 브리핑 에이전트 실행 중...")

    days_data = _load_from_supabase(7)
    if not days_data:
        print("  ⚠️  Supabase에서 데이터를 가져올 수 없음 — 스킵")
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
