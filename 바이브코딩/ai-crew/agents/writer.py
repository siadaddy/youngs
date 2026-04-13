import re
import time
from utils.gemini_client import ask_gemini

# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════
# 상수
# ═══════════════════════════════════════════════════════════════

BLACKLIST = [
    "와 이거 실화야", "와 이거", "와 이 ", "레전드네", "레전드다",
    "헐 이거", "대박이다", "대박이야", "실화냐", "정말 인상적이야",
    "관심이 생긴다", "관심이 집중된다", "지켜봐야겠다", "어떻게 될지 궁금",
]

_TITLE_STOP = {
    '을','를','이','가','의','은','는','에','도','와','과','로','으로',
    '그','및','등','관련','대한','위한','따른','하는','했다','있다',
}

_QUALITY_PATTERNS = [
    (r'[ㄱ-ㅎㅏ-ㅣ]{2,}',            '깨진 자모'),
    (r'[\u4e00-\u9fff]',              '한자 혼입'),
    (r'[\u00c0-\u024f]',              '라틴확장(독어 등)'),
    (r'[\uac00-\ud7af]{1,3}이이|[\uac00-\ud7af]{1,3}가가', '조사 중복'),
    (r'더[가-힣]{0,3}되더니',         '미완성 문장'),
    (r'더욱\s*되었어|성공적으로\s*된다면', '미완성 문장'),
    (r'(?<=[가-힣])[가-힣]{0,2}(?:하다|되다)(?:더니|더라)(?!\s)', '어색한 연결'),
    (r'더욱[가-힣]{0,2}시킬',         '붙여쓰기(더욱~시킬)'),
    (r'[가-힣]+\s*운\s*시장',         '오탈자(운송시장)'),
    (r'습니다\.|겠습니다\.|됩니다\.',  '격식체 혼입'),
]

_SENT_STOP = {
    "을","를","이","가","의","은","는","에","도","와","과","로","으로",
    "그","및","등","이다","있다","하다","됩니다","합니다","했다","있어",
    "하는","한다","된다","했어","이야","거야","이에","따라","위해",
}

_TOPIC_STOP = {
    "을","를","이","가","의","은","는","에","도","와","과","로","으로","그","및","등","관련",
}


# ═══════════════════════════════════════════════════════════════
# 순수 체크 함수 (side-effect 없음, API 호출 없음)
# ═══════════════════════════════════════════════════════════════

def _check_blacklist(text: str) -> list:
    return [p for p in BLACKLIST if p in text]


def _check_title(headline: str, text: str) -> bool:
    """제목 핵심 키워드의 40% 이상이 본문에 있으면 True"""
    words = {w for w in re.sub(r'[^\w\s]', '', headline).split()
             if len(w) > 1 and w not in _TITLE_STOP}
    if not words:
        return True
    return sum(1 for w in words if w in text) / len(words) >= 0.4


def _check_quality_patterns(text: str) -> list:
    return [desc for pat, desc in _QUALITY_PATTERNS if re.search(pat, text)]


def _count_hashtags(text: str) -> int:
    return len(re.findall(r'#[가-힣A-Za-z0-9_]+', text))


def _sent_tokens(text: str) -> set:
    return {t for t in re.sub(r'[^\w\s]', '', text).split()
            if len(t) > 1 and t not in _SENT_STOP}


def _detect_repetition(text: str) -> list:
    """유사 문장 쌍 (토큰 70% 이상 겹침) 목록 반환"""
    body = re.sub(r'#[가-힣A-Za-z0-9_]+', '', text)
    body = re.sub(r'##[^\n]*', '', body)
    raw = re.split(r'(?<=[다야요죠])\.\s+|(?<=[!?])\s+|(?<=\.)\s+', body)
    sents = [s.strip() for s in raw if len(s.strip()) > 15]
    pairs = []
    for i in range(len(sents)):
        for j in range(i + 1, len(sents)):
            ka, kb = _sent_tokens(sents[i]), _sent_tokens(sents[j])
            if not ka or not kb:
                continue
            overlap = len(ka & kb) / min(len(ka), len(kb))
            if overlap >= 0.70:
                pairs.append((sents[i][:40], sents[j][:40], round(overlap, 2)))
    return pairs


def _topic_overlap(a: str, b: str) -> float:
    """두 제목의 핵심 키워드 겹침 비율"""
    def kw(s):
        return {w for w in s.replace(",", "").replace(".", "").split()
                if len(w) > 1 and w not in _TOPIC_STOP}
    ka, kb = kw(a), kw(b)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / min(len(ka), len(kb))


# ═══════════════════════════════════════════════════════════════
# 자동 교정 함수 (API 호출 없음)
# ═══════════════════════════════════════════════════════════════

def _fix_hashtag_position(text: str) -> str:
    """본문 중간에 박힌 해시태그 블록을 맨 끝으로 이동"""
    lines = text.split('\n')
    hashtag_lines, body_lines = [], []
    for line in lines:
        stripped = line.strip()
        if stripped and re.match(r'^(#[가-힣A-Za-z0-9_]+\s*)+$', stripped):
            hashtag_lines.append(stripped)
        else:
            body_lines.append(line)
    if not hashtag_lines:
        return text
    body = '\n'.join(body_lines).rstrip()
    tags = ' '.join(hashtag_lines)
    return f"{body}\n\n{tags}"


def _trim_section(content: str) -> str:
    """섹션 내용을 최대 2문장, 300자 이내로 정리"""
    content = content.strip()
    sents = re.split(r'(?<=[다야요죠])\.\s+', content)
    sents = [s.strip() for s in sents if s.strip()]
    if len(sents) >= 2:
        result = sents[0].rstrip('.') + '. ' + sents[1].rstrip('.') + '.'
    elif sents:
        result = sents[0] if sents[0].endswith('.') else sents[0] + '.'
    else:
        result = content
    if len(result) > 300:
        cut = result[:300]
        for p in ['.', '!', '?']:
            pos = cut.rfind(p)
            if pos > 80:
                result = cut[:pos + 1]
                break
        else:
            result = cut
    return result


def _enforce_editor_structure(text: str) -> str:
    """## 소제목 아래 각 섹션: 2문장 / 300자 이내로 후처리"""
    hashtag_match = re.search(r'\n\n((?:#[가-힣A-Za-z0-9_]+ *)+)\s*$', text)
    hashtags = hashtag_match.group(1).strip() if hashtag_match else ""
    body = text[:hashtag_match.start()] if hashtag_match else text
    segments = re.split(r'(\n## [^\n]+)', body)
    output = [segments[0]]
    i = 1
    while i < len(segments):
        output.append(segments[i])
        i += 1
        if i < len(segments) and not segments[i].lstrip().startswith('## '):
            output.append('\n' + _trim_section(segments[i]) + '\n')
            i += 1
    result = ''.join(output)
    return (result.rstrip() + '\n\n' + hashtags) if hashtags else result


# ═══════════════════════════════════════════════════════════════
# 통합 품질 검사
# ═══════════════════════════════════════════════════════════════

def quality_check(
    text: str,
    headline: str = "",
    check_repetition: bool = False,
) -> dict:
    """
    모든 품질 검사를 수행하고 결과를 반환.

    Returns:
        {
          "passed": bool,
          "issues": list[str],   # 실패 항목명
          "hints":  list[str],   # 재생성 프롬프트에 추가할 힌트
        }
    """
    issues, hints = [], []

    # 1. 블랙리스트
    bl = _check_blacklist(text)
    if bl:
        issues.append(f"블랙리스트: {bl}")
        hints.append("⚠️ 아래 표현 절대 사용 금지: " + ", ".join(f'"{p}"' for p in bl))

    # 2. 제목-본문 일치
    if headline and not _check_title(headline, text):
        issues.append("제목-본문 불일치")
        hints.append(f"⚠️ 필수: 제목 '{headline}'의 기업명·인물명·주제가 반드시 본문에 포함되어야 합니다.")

    # 3. 문장 품질 패턴
    qp = _check_quality_patterns(text)
    if qp:
        issues.append(f"품질 오류: {qp}")
        hints.append("⚠️ 깨진 자모·한자·외국어·격식체(습니다/됩니다) 절대 금지.")

    # 4. 해시태그 개수
    ht_count = _count_hashtags(text)
    if ht_count < 8:
        issues.append(f"해시태그 {ht_count}개 (8개 미만)")
        hints.append("⚠️ 해시태그 8개 이상 필수. 본문 맨 끝에 한 줄로.")

    # 5. 반복 문장 (블로그만)
    if check_repetition:
        reps = _detect_repetition(text)
        if reps:
            issues.append(f"반복 문장 {len(reps)}쌍")
            hints.append(
                "⚠️ 반복 문장 절대 금지: 이미 쓴 내용을 다른 표현으로 바꿔 반복하는 것도 금지."
                " 각 문장은 새로운 정보를 담아야 해."
            )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "hints":  hints,
    }


# ═══════════════════════════════════════════════════════════════
# 생성 + 품질 게이트 루프
# ═══════════════════════════════════════════════════════════════

def _ensure_complete(article: str, prompt: str) -> str:
    """아티클이 완전한 문장으로 끝나지 않으면 이어서 완성"""
    article = article.strip()
    if any(article.endswith(e) for e in (
        '다.', '요.', '습니다.', '입니다.', '겠습니다.',
        '됩니다.', '합니다.', '이다.', '!', '?'
    )):
        return article
    print("  ⚠️  아티클 미완성 → 이어서 작성 중...")
    cont = ask_gemini(
        f"아래 블로그 글이 끊겼습니다. 끊긴 부분부터 결론까지만 이어서 완성하세요."
        f" 앞부분 반복 금지.\n\n[끊긴 글]\n{article[-500:]}",
        system=SYSTEM, temperature=0.7, max_tokens=2048,
    )
    return article + "\n" + cont.strip()


def _generate_with_quality(
    prompt: str,
    headline: str,
    label: str,
    max_tokens: int,
    temperature: float,
    is_blog: bool = False,
    check_repetition: bool = False,
    max_retries: int = 2,
) -> tuple:
    """
    텍스트 생성 후 quality_check를 통과할 때까지 재생성.
    자동 교정(해시태그 위치, 에디터 구조)은 매 시도마다 적용.

    Returns: (text: str, retry_count: int)
    """
    def _autofix(t: str) -> str:
        t = _fix_hashtag_position(t)
        if is_blog:
            t = _enforce_editor_structure(t)
        return t

    # 초기 생성
    text = ask_gemini(prompt, system=SYSTEM, temperature=temperature, max_tokens=max_tokens)
    if is_blog:
        text = _ensure_complete(text, prompt)
    text = _autofix(text)
    result = quality_check(text, headline, check_repetition=check_repetition)

    if result["passed"]:
        return text, 0

    # 재생성 루프 (최대 max_retries회)
    for attempt in range(1, max_retries + 1):
        print(f"  ⚠️  [{label}] 품질 실패 → 재생성 {attempt}/{max_retries} | 이슈: {result['issues']}")
        hint_block = "\n".join(result["hints"])
        new_prompt = f"{prompt}\n\n{hint_block}"
        time.sleep(3)
        text = ask_gemini(
            new_prompt, system=SYSTEM,
            temperature=min(temperature + 0.06 * attempt, 0.95),
            max_tokens=max_tokens,
        )
        if is_blog:
            text = _ensure_complete(text, new_prompt)
        text = _autofix(text)
        result = quality_check(text, headline, check_repetition=check_repetition)
        if result["passed"]:
            print(f"  ✅ [{label}] {attempt}회 재생성 후 품질 통과")
            return text, attempt

    print(f"  ⚠️  [{label}] {max_retries}회 재생성 후에도 미통과 {result['issues']} — 그대로 사용")
    return text, max_retries


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════

def run(brief: dict) -> dict:
    print("✍️  작가 에이전트 실행 중...")
    quality_log = []  # (label, retry_count)

    # ── 카드뉴스 ───────────────────────────────────────────────
    captions = []
    for i, item in enumerate(brief["instagram"]):
        label = f"카드{i + 1}"

        source_facts = item.get('source_facts', '')
        if isinstance(source_facts, list):
            source_facts = ' '.join(str(s) for s in source_facts)
        source_facts = str(source_facts)
        facts_note = (
            f"\n실제 사실 (이것만 써, 없는 건 창작 금지):\n{source_facts}\n"
            if source_facts.strip() else ""
        )

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
- 해시태그를 본문 중간에 삽입하는 것 — 해시태그는 반드시 본문이 끝난 후 맨 마지막에만
- 한글 단어를 한자로 혼용 (車량, 金錢 등)
- 독일어·베트남어 등 한국어·영어 아닌 외국어
- 없는 수치·사실 창작
- 제목에 등장한 기업명·인물명·주제가 본문에 전혀 없는 경우 (제목과 본문 주제 일치 필수)

본문(해시태그 제외) 120~200자. 글 다 쓴 뒤 빈 줄 두 개 → 해시태그 8개를 한 줄에. 해시태그는 반드시 #단어 형식 (빈 # 금지). 해시태그를 본문 사이에 넣으면 실패.
"""
        caption, retries = _generate_with_quality(
            prompt, item["headline"], label,
            max_tokens=1200, temperature=0.7,
        )
        quality_log.append((label, retries))

        # 카드 간 주제 중복 감지 — 로그만 (planner 단에서 수정 필요)
        for prev in captions:
            overlap = _topic_overlap(item["headline"], prev["headline"])
            if overlap >= 0.7:
                print(
                    f"  ⚠️  [{label}] 주제 중복 경고 ({overlap:.0%})"
                    f" — '{prev['headline'][:30]}'와 유사 (planner 점검 필요)"
                )

        captions.append({
            "headline":    item["headline"],
            "caption":     caption,
            "source_url":  item.get("source_url", ""),
            "source_name": item.get("source_name", ""),
        })
        print(f"  ✅ {label} 완성 ({len(caption)}자, 재생성 {retries}회)")
        if i < len(brief["instagram"]) - 1:
            time.sleep(5)

    # ── 블로그 아티클 ──────────────────────────────────────────
    b = brief["blog"]
    blog_source_facts = b.get('source_facts', '')
    if isinstance(blog_source_facts, list):
        blog_source_facts = ' '.join(str(s) for s in blog_source_facts)
    blog_source_facts = str(blog_source_facts).strip()
    facts_block = (
        f"\n참고할 실제 사실 (이것만 사실로 써, 없는 건 창작 금지):\n{blog_source_facts}\n"
        if blog_source_facts else ""
    )

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
- 동일한 주어+서술어 조합 2회 이상 사용 금지
- 각 문단은 반드시 새로운 정보·시각 포함 — 같은 내용을 다른 표현으로 반복 금지
- 각 ## 소제목 아래: 이전 섹션에서 언급하지 않은 새로운 내용만. 재진술·요약 금지.
- "개인적으로는 ~을 바란다", "~이루어지길 바라는 마음으로 글을 마치며" 같은 편집자 개인 의견 표명
- 한글 단어를 한자로 혼용 / 한국어·영어 외 외국어

분량 700~900자. 억지로 늘리지 마. 마지막 문장은 마침표로.
글 다 쓰고 빈 줄 두 개 뒤에 해시태그 8개. 해시태그는 반드시 #단어 형식 (빈 # 금지).
"""
    article = ""
    try:
        article, retries = _generate_with_quality(
            blog_prompt, b["title"], "블로그",
            max_tokens=2000, temperature=0.88,
            is_blog=True, check_repetition=True,
        )
        quality_log.append(("블로그", retries))
        print(f"  ✅ 블로그 아티클 완성 ({len(article)}자, 재생성 {retries}회)")
    except Exception as e:
        print(f"  ⚠️  블로그 아티클 실패 (카드뉴스는 유지): {e}")

    # ── 품질 요약 로그 ─────────────────────────────────────────
    total_retries = sum(r for _, r in quality_log)
    regen_items = [(l, r) for l, r in quality_log if r > 0]
    if regen_items:
        detail = ", ".join(f"{l}:{r}회" for l, r in regen_items)
        print(f"\n  📊 품질 요약: 총 재생성 {total_retries}회 — {detail}")
    else:
        print(f"\n  📊 품질 요약: 전체 품질 통과 (재생성 0회)")

    return {"captions": captions, "article": article, "blog_title": b["title"]}
