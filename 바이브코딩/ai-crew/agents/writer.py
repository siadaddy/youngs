from utils.gemini_client import ask_gemini

SYSTEM = """
너는 '시아아빠'야. 40대 직장인, BMW 딜러 근무.
매일 아침 뉴스 보고 느낀 점 인스타·블로그에 올리는 사람이야.

글 쓸 때 이것만 지켜:
- 친구한테 카톡 보내듯. 근데 내용은 진짜 있게.
- 첫 반응은 솔직하게 ("와 이거 실화야", "솔직히 나도 몰랐는데", "이거 보고 좀 웃겼어")
- 어려운 내용도 쉽게. 뉴스 안 보는 친구도 이해하게.
- 내 생각 자연스럽게 끼워넣기. 근데 "개인적으로는" 같은 말투 너무 반복하지 마.
- 짧은 문장이랑 긴 문장 섞어서 리듬감 줘. 단조롭게 쭉 이어지면 지루함.
- 보고서처럼 딱딱하게 쓰면 안 돼. 제목/소제목 레이블 달지 마.
- 한국어 위주. 영어는 AI, 뉴스처럼 자연스러운 것만.
- 이모지 1~2개만. 많으면 가벼워 보임.
"""

def run(brief: dict) -> dict:
    print("✍️  작가 에이전트 실행 중...")

    captions = []
    for i, item in enumerate(brief["instagram"]):
        source_facts = item.get('source_facts', '')
        if isinstance(source_facts, list):
            source_facts = ' '.join(str(s) for s in source_facts)
        source_facts = str(source_facts)
        facts_note = f"\n실제 사실 (이것만 써, 없는 건 창작 금지):\n{source_facts}\n" if source_facts.strip() else ""
        prompt = f"""인스타그램 카드뉴스 캡션 써줘. 주제: "{item['headline']}"
{facts_note}
각도: {item['angle']}
톤: {item['tone']}

첫 줄에 이모지 하나 + 스크롤 멈추게 하는 한 문장으로 시작해.
그 다음엔 이게 왜 중요한지 쉽게 풀어주고, 핵심 사실 2~3줄.
없는 수치나 사실 창작은 절대 금지. 마지막은 짧게 생각이나 질문으로 마무리.
전체 400~500자. 레이블([사실], [분석] 같은 거) 절대 달지 마.
한국어만. 한자·아랍어 등 이상한 문자 절대 금지.

글 다 쓰고 나서 줄바꿈 두 번 하고 해시태그 8개 써줘. (예시 형식: #뉴스 #경제 ...)
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
    blog_source_facts = b.get('source_facts', '')
    if isinstance(blog_source_facts, list):
        blog_source_facts = ' '.join(str(s) for s in blog_source_facts)
    blog_source_facts = str(blog_source_facts).strip()

    facts_block = f"\n참고할 실제 사실 (이것만 사실로 써, 없는 건 창작 금지):\n{blog_source_facts}\n" if blog_source_facts else ""

    blog_prompt = f"""오늘 뉴스 중에 "{b['title']}" 얘기가 있었어.
{facts_block}
이걸 주제로 블로그 글 한 편 써줘.

핵심 포인트: {', '.join(b['main_points'])}

뉴스 봤을 때 첫 반응으로 시작해 (인사말 금지).
뉴스 모르는 사람도 이해하게 쉽게 풀어줘.
소제목(##)은 2개 정도만, 대화체로 달기. 보고서 제목 말고.
중간중간 내 생각/의견 자연스럽게. 근데 같은 표현 계속 반복하지 마.
마지막은 짧게 여운 남기고 마침표로 끝내.
분량은 800~1000자. 억지로 늘리지 마.
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
