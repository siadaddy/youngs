import json
from utils.gemini_client import ask_gemini

SYSTEM = """
당신은 30년 경력의 시니어 디지털 콘텐츠 기획자입니다.
조선일보, 중앙일보, 네이버 등 국내 주요 미디어사에서 편집장을 역임했으며,
SNS 바이럴 콘텐츠 기획의 최고 전문가입니다.
독자 심리와 알고리즘을 동시에 꿰뚫는 전략적 안목으로
어떤 뉴스가 사람들의 마음을 움직이는지 본능적으로 압니다.
항상 JSON 형식으로만 응답하세요.
"""

def run(newsletter_text: str) -> dict:
    print("🎯 기획자 에이전트 실행 중...")

    prompt = f"""
다음 뉴스레터에서 오늘의 핵심 뉴스를 선정하고 콘텐츠 브리프를 작성해주세요.

[뉴스레터]
{newsletter_text}

아래 JSON 형식으로 정확히 응답하세요:
{{
  "instagram": [
    {{
      "headline": "핵심 제목 (30자 이내)",
      "angle": "인스타 포스트 각도/관점",
      "keywords": ["키워드1", "키워드2", "키워드3"],
      "tone": "정보전달 | 감성적 | 충격적 | 유머"
    }}
  ],
  "blog": {{
    "title": "블로그 아티클 제목",
    "main_points": ["핵심 포인트1", "핵심 포인트2", "핵심 포인트3"],
    "tone": "전문적이고 읽기 쉬운 문체",
    "target": "타겟 독자층"
  }}
}}

instagram은 5개, blog는 1개만 작성하세요.
🚗 필수 규칙: instagram 배열의 첫 번째(index 0) 항목은 반드시 자동차, BMW, 전기차, 모빌리티, 자율주행 관련 뉴스여야 합니다.
   - 해당 뉴스가 없으면 자동차 업계 전반 또는 수입차 시장 트렌드라도 첫 번째로 배치하세요.
   - 나머지 4개는 다른 카테고리에서 자유롭게 선정합니다.
⚠️ 중복 금지: 5개 선정 시 같은 주제·인물·회사·사건이 2번 이상 나오면 절대 안 됩니다.
   예) "기름값 상승" + "유가 급등" → 동일 주제 → 하나만 선정, 나머지는 다른 주제로 교체.
   5개는 반드시 서로 다른 카테고리 또는 전혀 다른 관점의 뉴스여야 합니다.
JSON 외 다른 텍스트는 절대 포함하지 마세요.
"""
    raw = ask_gemini(prompt, system=SYSTEM, temperature=0.6)

    # JSON 파싱 (마크다운 코드블록 제거)
    raw = raw.replace("```json", "").replace("```", "").strip()
    brief = json.loads(raw)

    total = len(brief['instagram'])
    print(f"  ✅ 인스타 {total}개, 블로그 1개 브리프 완성")
    return brief
