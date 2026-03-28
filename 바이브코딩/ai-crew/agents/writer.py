from utils.gemini_client import ask_gemini

SYSTEM = """
당신은 30년 경력의 수석 저널리스트이자 SNS 콘텐츠 전문가입니다.
KBS, MBC, 한겨레 등 국내 주요 언론사에서 기자와 앵커로 활동했으며,
100만 구독자 유튜브 채널과 50만 팔로워 인스타그램을 직접 운영한 경험이 있습니다.
독자가 첫 줄을 읽는 순간 멈추게 만드는 훅, 사실에 기반한 깊이 있는 분석,
그리고 독자의 감정을 움직이는 스토리텔링이 당신의 최대 강점입니다.
절대 짧거나 성의 없는 글은 쓰지 않습니다. 항상 지정된 분량을 넘겨서 작성합니다.
한국어와 영어, 이모지만 사용합니다. 한자·아랍어·태국어 등 다른 언어는 절대 사용하지 않습니다.
"""

def run(brief: dict) -> dict:
    print("✍️  작가 에이전트 실행 중...")

    captions = []
    for i, item in enumerate(brief["instagram"]):
        prompt = f"""
아래 뉴스 브리프로 카드뉴스 글을 작성해주세요.

헤드라인: {item['headline']}
각도: {item['angle']}
키워드: {', '.join(item['keywords'])}
톤: {item['tone']}

━━━ 작성 구조 (반드시 이 순서대로) ━━━

1. 훅 (1~2줄)
   - 이모지로 시작
   - 독자가 멈추게 만드는 강렬한 첫 문장
   - 질문형 또는 충격적 사실로 시작

2. 배경 설명 (3~4문장)
   - 왜 이 뉴스가 중요한가
   - 구체적 수치나 사실 반드시 포함 (출처: 매체명 표기)
   - 독자가 몰랐을 맥락 설명

3. 핵심 팩트 (3~4문장) — 각 문장을 반드시 줄바꿈 후 [사실] 레이블로 시작
   - 형식: (빈 줄) → "[사실] 확인된 사실 문장." → (줄바꿈) → "[사실] 다음 사실."
   - 확인된 사실만, 구체적 날짜·수치·주체 명시
   - 이모지로 포인트 강조

4. 분석 & 전망 (각 1~2문장) — 줄바꿈 후 레이블로 시작
   - 형식: (빈 줄) → "[분석] 분석 내용." → (줄바꿈) → "[전망] 전망 내용."
   - 독자에게 실질적으로 의미하는 바, 앞으로 어떻게 될지

5. 행동 유도 (1줄)
   - "저장하고 나중에 읽어봐요!" 또는 "의견은 댓글로!" 등

6. 해시태그 (20개, 줄바꿈 후)
   - 뉴스 관련 구체 해시태그 + 일반 해시태그 혼합

━━━ 규칙 ━━━
- 전체 글 최소 500자 이상 (해시태그 제외)
- 텍스트만 출력 (설명, 번호, 섹션 제목 없이)
- 각 섹션 사이 빈 줄 하나
- [사실] / [분석] / [전망] 은 반드시 줄의 맨 앞에서 시작 (절대 문장 중간에 삽입 금지)
- 한국어·영어·이모지만 사용 (한자·아랍어 등 절대 금지)
"""
        caption = ask_gemini(prompt, system=SYSTEM, temperature=0.85, max_tokens=1200)
        captions.append({"headline": item["headline"], "caption": caption})
        print(f"  ✅ 카드뉴스 {i+1}/5 완성 ({len(caption)}자)")
        if i < len(brief["instagram"]) - 1:
            import time; time.sleep(20)   # TPM 한도 초과 방지 (6000 TPM / ~1400 per call)

    # 블로그 아티클
    b = brief["blog"]
    blog_prompt = f"""
아래 브리프로 블로그 아티클을 완성해주세요.

제목: {b['title']}
핵심 포인트: {', '.join(b['main_points'])}
문체: {b['tone']}
타겟: {b['target']}

━━━ 작성 규칙 ━━━
- 마크다운 형식 (# 제목, ## 소제목)
- 전체 분량 최소 1500자 이상 (반드시 완성할 것)
- 소제목(##) 4개 이상
- 각 소제목 아래 최소 3~4문장 이상
- 도입부: 독자의 관심을 끄는 질문이나 상황 제시 (150자 이상)
- 본문: 구체적 수치, 사례, 전문가 의견 포함
- 결론: 핵심 요약 + 독자에게 전하는 인사이트로 마무리

절대로 중간에 끊지 말고 끝까지 완성하세요.
마지막 문장은 반드시 마침표(.)로 끝내야 합니다.
"""
    article = ask_gemini(blog_prompt, system=SYSTEM, temperature=0.7, max_tokens=3000)

    # 완성 여부 체크 — 마지막 문장이 끊겼으면 이어서 완성
    article = _ensure_complete(article, blog_prompt)

    print(f"  ✅ 블로그 아티클 완성 ({len(article)}자)")

    return {"captions": captions, "article": article, "blog_title": b["title"]}


def _ensure_complete(article: str, original_prompt: str) -> str:
    """아티클이 완전한 문장으로 끝나지 않으면 이어서 완성"""
    article = article.strip()
    complete_endings = ('다.', '요.', '습니다.', '입니다.', '겠습니다.',
                        '됩니다.', '합니다.', '이다.', '!', '?')
    if any(article.endswith(e) for e in complete_endings):
        return article

    print("  ⚠️  아티클 미완성 감지 → 이어서 작성 중...")
    continuation_prompt = f"""
아래 블로그 글이 중간에 끊겼습니다. 이어서 완성해주세요.
끊긴 부분부터 자연스럽게 이어서 결론까지 작성하세요.

[끊긴 글]
{article[-500:]}

위 내용에 이어서 나머지 부분만 작성하세요. (앞부분 반복 금지)
반드시 완전한 문장으로 끝내세요.
"""
    continuation = ask_gemini(continuation_prompt, system=SYSTEM, temperature=0.7, max_tokens=2048)
    return article + "\n" + continuation.strip()
