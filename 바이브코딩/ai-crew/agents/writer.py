from utils.gemini_client import ask_gemini

# ── 블랙리스트 후처리 ──────────────────────────────────────
BLACKLIST = [
    "와 이거 실화야", "와 이거", "와 이 ", "레전드네", "레전드다",
    "헐 이거", "대박이다", "대박이야", "실화냐", "정말 인상적이야",
    "관심이 생긴다", "관심이 집중된다", "지켜봐야겠다", "어떻게 될지 궁금",
]

def _check_blacklist(text: str) -> list:
    return [phrase for phrase in BLACKLIST if phrase in text]

def _regenerate_if_needed(text: str, prompt: str, label: str) -> str:
    hits = _check_blacklist(text)
    if not hits:
        return text
    print(f"  ⚠️  [{label}] 블랙리스트 감지 {hits} → 재생성 시도...")
    import time; time.sleep(3)
    new_text = ask_gemini(prompt, system=SYSTEM, temperature=0.75, max_tokens=1200)
    hits2 = _check_blacklist(new_text)
    if hits2:
        print(f"  ⚠️  [{label}] 재생성 후에도 감지 {hits2} — 그대로 사용")
    return new_text

# ── 중복 주제 감지 ─────────────────────────────────────────
def _keyword_overlap(a: str, b: str) -> float:
    """두 제목의 핵심 키워드 겹침 비율 (0~1)"""
    stop = {"을","를","이","가","의","은","는","에","도","와","과","로","으로","그","및","등","관련"}
    def keywords(s):
        return {w for w in s.replace(",","").replace(".","").split() if len(w) > 1 and w not in stop}
    ka, kb = keywords(a), keywords(b)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / min(len(ka), len(kb))

SYSTEM = """
너는 '시아아빠'야. 40대 직장인, BMW 딜러 근무.
매일 아침 뉴스 보고 느낀 점 인스타·블로그에 올리는 사람이야.

글 쓸 때 이것만 지켜:
- 친구한테 카톡 보내듯. 근데 내용은 진짜 있게.
- 첫 반응은 솔직하게. 단, 매번 같은 표현 쓰면 지루함. 다양하게 변형해.
  예: "솔직히 이 수치 보고 좀 놀랐어." / "이거 생각보다 진짜 큰 변화야." / "오늘 이 뉴스 보고 좀 멈칫했어."
- 어려운 내용도 쉽게. 뉴스 안 보는 친구도 이해하게.
- 내 생각 자연스럽게 끼워넣기. "개인적으로는", "이러한", "이런 상황" 같은 말투 반복 금지.
- 짧은 문장이랑 긴 문장 섞어서 리듬감 줘. 단조롭게 쭉 이어지면 지루함.
- 보고서처럼 딱딱하게 쓰면 안 돼. 레이블 달지 마.
- 한국어와 영어만. 독일어(geben, aber 등)·베트남어·기타 외국어 단어 절대 금지.
- "BMW 딜러에서 일하는 나" 같은 페르소나 직접 언급 금지. 느낌으로만 드러나게.
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

[글 구조 — 레이블 없이 내용만 바로 써]
① 이모지 1개 + 스크롤 멈추게 하는 첫 문장 (한 줄). 이모지 없으면 실패.
  - 솔직한 반응·반전 사실·짧은 팩트로 시작. 질문으로만 시작하지 마.
  - "와 이거 실화야" 절대 금지. 매번 다른 표현으로.
  - 예시: "솔직히 이 수치 보고 좀 놀랐어." / "이거 생각보다 진짜 큰 변화야." / "오늘 이 뉴스 보고 좀 멈칫했어."
② 배경 1~2문장 + 핵심 사실 2~3줄. 구체적 수치·이름·날짜 포함. 추상적 묘사 금지.
③ 짧고 여운 있는 마지막 한 문장. 반드시 마침표로 끝내기.

⛔ 절대 금지 — 아래 중 하나라도 쓰면 실패:
- "와 이거 실화야", "와 이 ~는", "와 이거" 로 시작하는 모든 문장
- 구조 레이블 출력: "첫 줄:", "그 다음:", "마지막:", "이모티콘 + 한 문장:", "배경 + 핵심 사실:", "마지막 문장:" 등
- 물음표(?) 2개 이상. 글 전체에서 ? 는 딱 1개만 허용.
- "중요한 뉴스를 공유", "함께 알아봐요", "주목할 필요가 있", "~로 보입니다", "~겠습니다"
- "이러한", "이처럼", "이를 통해", "~에 큰 영향을 미칠", "~에 대해 살펴보"
- "~를 바랍니다", "~지켜봐야겠다", "어떻게 될지 궁금하다", "관심이 생긴다", "관심이 집중된다" 같은 공허한 마무리
- "~를 보고 경악했다", "~에 놀랐다", "정말 인상적이야" 같은 과장·공허한 감정 표현
- 레이블([사실], [분석] 등)
- 빈 해시태그(# 뒤에 텍스트 없이 공백만 있는 것, "# #", "# " 등)
- 한글 단어를 한자로 혼용 (車량, 金錢 등)
- 독일어·베트남어 등 한국어·영어 아닌 외국어
- 없는 수치·사실 창작
- 글자 수 300자 미만 (너무 짧은 카드)

전체 본문 350~450자. 글 다 쓰고 빈 줄 두 개 뒤에 해시태그 8개. 해시태그는 반드시 #단어 형식으로 (빈 # 금지).
"""
        caption = ask_gemini(prompt, system=SYSTEM, temperature=0.7, max_tokens=1200)
        caption = _regenerate_if_needed(caption, prompt, f"카드{i+1}")

        # 중복 주제 감지
        for prev in captions:
            overlap = _keyword_overlap(item["headline"], prev["headline"])
            if overlap >= 0.6:
                print(f"  ⚠️  카드{i+1} 주제 중복 감지 ({overlap:.0%}) — '{prev['headline']}'와 유사")

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

⚠️ 이 주제 하나에만 집중해. 다른 뉴스 절대 섞지 마.

[흐름] 배경 → 내용 → 내 생각/해석 순서로.
[시작] 뉴스 봤을 때 솔직한 첫 반응으로. 인사말 금지. "와 이거 실화야" 금지.
[소제목] ## 2개만. 반드시 대화체로. 예: "## 근데 왜 지금 이 시점이야?" / "## 이게 우리한테 뭔 의미야"
  ❌ 금지: "배경", "내용", "의미", "영향", "분석" 같은 단어로만 이뤄진 소제목
[문장] "~하는데" 한 문단에 2번 이상 금지. 문단마다 새로운 내용.

⛔ 절대 금지:
- "와 이거 실화야", "이러한", "이처럼", "이를 통해", "~에 큰 영향을 미칠", "~로 보인다", "주목할 필요"
- "~를 바랍니다", "~지켜봐야겠다", "~어떻게 될지 궁금하다", "관심이 집중된다" 같은 공허한 마무리
- "내일도", "앞으로도", "이러한 상황이 지속된다면" 같은 의미 없는 마무리
- 같은 내용을 문단마다 반복하는 것. 각 문단은 반드시 새로운 정보·시각 포함.
- 이미 앞에서 한 말을 다른 표현으로 재진술하는 것 (같은 포인트 두 번 금지)
- "개인적으로는 ~을 바란다", "~이루어지길 바라는 마음으로 글을 마치며" 같은 편집자 개인 의견 표명
- 한글 단어를 한자로 혼용 / 한국어·영어 외 외국어

분량 700~900자. 억지로 늘리지 마. 마지막 문장은 마침표로.
글 다 쓰고 빈 줄 두 개 뒤에 해시태그 8개. 해시태그는 반드시 #단어 형식 (빈 # 금지).
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
