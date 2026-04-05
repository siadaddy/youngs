from utils.gemini_client import ask_gemini

SYSTEM = """
너는 '시아아빠'야. 40대 직장인이고 BMW 딜러에서 일해.
매일 아침 뉴스 읽고 느낀 점을 블로그에 적는 걸 즐기는 사람이야.
글 스타일: 친구한테 카톡 보내듯 편하게, 근데 내용은 진짜 있게.
- 첫 문장은 무조건 내 반응/감정으로 시작 ("와 이거 진짜야?", "솔직히 나도 몰랐는데", "이거 보고 좀 놀랐어")
- 복잡한 내용도 쉽게 풀어서 설명 (내 친구가 뉴스 안 봐도 이해하게)
- 중간에 내 생각/의견 반드시 포함 ("근데 내 생각엔", "개인적으론", "솔직히")
- 문장 길이 다양하게. 짧은 거, 긴 거 섞어.
- 너무 형식적이거나 보고서 같으면 안 돼
- 한국어만. 영어 단어 섞는 건 자연스러운 정도만 (뉴스, AI 같은 거)
- 이모지는 1~2개만, 남발 금지
"""

def run(brief: dict) -> dict:
    print("✍️  작가 에이전트 실행 중...")

    captions = []
    for i, item in enumerate(brief["instagram"]):
        source_facts = item.get('source_facts', '')
        facts_note = f"\n실제 사실 (이것만 써, 없는 건 창작 금지):\n{source_facts}\n" if source_facts.strip() else ""
        prompt = f"""인스타그램 카드뉴스 글 써줘. 주제는 "{item['headline']}"야.
{facts_note}
각도: {item['angle']}
톤: {item['tone']}

--- 규칙 ---
- 첫 줄: 이모지 하나 + 사람 멈추게 하는 한 문장 (질문이나 반전 OK)
- 이유/배경 2~3문장: 왜 이게 중요한지 쉽게
- 핵심 내용 2~3줄: 실제 있는 사실만, 없는 수치 창작 금지
- 마지막: 짧은 생각/질문으로 마무리
- 해시태그 8개로 끝내기 (중복 없이)
- 전체 400~600자
- 섹션 제목([사실], [분석] 같은 레이블) 없이 자연스럽게
- 한국어만, 한자·아랍어·베트남어 절대 금지
"""
        caption = ask_gemini(prompt, system=SYSTEM, temperature=0.7, max_tokens=1200)
        captions.append({
            "headline":    item["headline"],
            "caption":     caption,
            "source_url":  item.get("source_url", ""),
            "source_name": item.get("source_name", ""),
        })
        print(f"  ✅ 카드뉴스 {i+1}/{len(brief['instagram'])} 완성 ({len(caption)}자)")
        if i < len(brief["instagram"]) - 1:
            import time; time.sleep(5)   # 라운드로빈 2키 분배로 TPM 2배 확보 → 5초로 단축

    # 블로그 아티클
    b = brief["blog"]
    blog_source_facts = b.get('source_facts', '').strip()

    facts_block = f"\n참고할 실제 사실 (이것만 사실로 써, 없는 건 창작 금지):\n{blog_source_facts}\n" if blog_source_facts else ""

    blog_prompt = f"""오늘 뉴스 중에 "{b['title']}" 이야기가 있었어.
{facts_block}
이걸 주제로 내 블로그에 글 한 편 써줘.

핵심 포인트: {', '.join(b['main_points'])}

--- 글 쓸 때 지켜야 할 것 ---
- 첫 문장: 이 뉴스 봤을 때 내 첫 반응으로 시작 (형식적인 인사말 금지)
- 중간에 내 의견/해석 자연스럽게 포함 ("솔직히", "근데", "나는" 같은 표현 OK)
- 뉴스를 모르는 사람도 이해하게 쉽게 설명
- 소제목(##)은 2~3개만, 딱딱한 보고서 제목 말고 대화체로
- 마지막은 짧게 내 생각/여운으로 마무리
- 분량: 800~1200자 (너무 길면 억지로 채운 느낌 남)
- 같은 표현 반복 절대 금지
- 마지막 문장은 마침표로 끝낼 것
"""
    # 블로그 실패해도 카드뉴스는 보존 — 부분 성공 허용
    article = ""
    try:
        article = ask_gemini(blog_prompt, system=SYSTEM, temperature=0.88, max_tokens=2000)
        article = _ensure_complete(article, blog_prompt)
        print(f"  ✅ 블로그 아티클 완성 ({len(article)}자)")
    except Exception as e:
        print(f"  ⚠️  블로그 아티클 실패 (카드뉴스는 유지): {e}")

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
