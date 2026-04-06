import json, re, html
from utils.gemini_client import ask_gemini

SYSTEM = """당신은 콘텐츠 브리프를 작성하는 편집자입니다. JSON만 출력합니다."""

NEWSLETTER_MAX_CHARS = 3000   # 토큰 절약 — 기사 원문 블록에 더 집중
ARTICLE_PER_CAT     = 3       # 카테고리당 원문 뉴스 최대 개수 (2→3)

def run(newsletter_text: str, newsletter_data: dict = None) -> dict:
    print("🎯 기획자 에이전트 실행 중...")

    # 뉴스레터 텍스트 길이 제한
    if len(newsletter_text) > NEWSLETTER_MAX_CHARS:
        newsletter_text = newsletter_text[:NEWSLETTER_MAX_CHARS] + "\n...(이하 생략)"

    # 카테고리별 원문 뉴스 — 제목 + summary(실제 본문) + URL 포함
    article_list_text = ""
    if newsletter_data and newsletter_data.get("categorized"):
        lines = []
        for cat, articles in newsletter_data["categorized"].items():
            for a in articles[:ARTICLE_PER_CAT]:
                title   = html.unescape(a.get("title", ""))
                link    = a.get("link", "")
                # summary 또는 body 키 모두 시도 (수집 방식에 따라 키 이름 다름)
                summary = html.unescape(
                    a.get("summary", "") or a.get("body", "")
                ).strip()[:400]
                if summary:
                    lines.append(f"[{cat}] {title}\n  내용: {summary}\n  URL: {link}")
                else:
                    lines.append(f"[{cat}] {title}\n  URL: {link}")
        article_list_text = "\n\n".join(lines)

    prompt = f"""아래 뉴스 데이터에서 오늘의 핵심 뉴스 5개를 골라 콘텐츠 브리프를 JSON으로 작성하세요.

=== 원문 뉴스 (제목 + 실제 내용 요약 + URL) ===
{article_list_text if article_list_text else newsletter_text}

=== 출력 JSON 형식 ===
{{
  "instagram": [
    {{
      "headline": "핵심 제목 (25자 이내, 클릭하고 싶어지는 제목)",
      "angle": "이 뉴스를 어떤 시각으로 볼 것인가 (한 줄)",
      "keywords": ["키워드1", "키워드2", "키워드3"],
      "tone": "정보전달 | 공감 | 놀라움 | 실용",
      "source_facts": "위 [내용]에서 직접 뽑은 구체적 사실들. 형식: '주체+행동+수치/결과' 로 2~4문장. 위 내용에 없는 건 절대 쓰지 마세요.",
      "source_url": "URL 그대로 복사",
      "source_name": "언론사명"
    }}
  ],
  "blog": {{
    "title": "오늘 뉴스 중 가장 임팩트 있는 단일 주제의 블로그 제목 (구체적 사건/기업/인물명 포함)",
    "main_points": [
      "이 사건의 배경 — 왜 생겼는가",
      "핵심 내용 — 구체적으로 무슨 일인가",
      "의미와 영향 — 앞으로 어떻게 될까"
    ],
    "tone": "친근하고 읽기 쉬운",
    "target": "뉴스에 관심 있는 30~40대",
    "source_facts": "위 [내용]에서 직접 뽑은 핵심 사실 4~6개. 수치·이름·날짜 포함. 없는 내용 창작 금지."
  }}
}}

규칙:
- instagram[0]: 반드시 자동차/BMW/전기차 관련. 없으면 자동차 업계 트렌드로 대체
- 5개 모두 서로 다른 주제 (같은 인물·사건 중복 금지)
- 제외: 범죄, 연예인 사생활, 정치 편향, 미검증 루머
- blog title: "뉴스레터 요약", "오늘의 뉴스", "뉴스 브리프", "4월 X일" 같은 날짜·요약성 제목 금지
- blog는 반드시 단일 뉴스 하나에만 집중 — main_points 3개 모두 같은 사건에 대한 것
- blog main_points는 "배경 → 내용 → 의미/영향" 구조로 작성
- JSON만 출력, 다른 텍스트 없이
"""
    raw = ask_gemini(prompt, system=SYSTEM, temperature=0.65, json_mode=True, max_tokens=2500)

    # JSON 파싱 — json_mode 보장 → 직접 파싱, 실패 시 regex 폴백
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        brief = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError(f"JSON 블록을 찾을 수 없음: {raw[:200]}")
        brief = json.loads(match.group())

    total = len(brief['instagram'])
    print(f"  ✅ 인스타 {total}개, 블로그 1개 브리프 완성")
    return brief
