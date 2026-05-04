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
- 첫 반응은 솔직하게. 단, 매번 같은 표현 절대 반복 금지. 글마다 완전히 다른 방식으로 시작해.
  ✅ 예: "숫자 하나가 눈에 박혔어." / "이거 생각보다 진짜 큰 변화야." / "딱 한 줄로 요약하면 이래." / "이 수치 보고 두 번 읽었어." / "솔직히 이건 예상 못 했어."
  ❌ 절대 금지: "오늘 이 뉴스 보고 좀 멈칫했어" / "오늘 아침 뉴스 보다가 멈칫했어" — 이 패턴 두 번 다시 쓰지 마.
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
    # 형용사+야 오탈자 (좋야, 많야, 높야, 큰야 등 — 받침 있는 어간 + 야)
    (r'(?:좋|많|높|낮|작|넓|좁|깊|얕|밝|어둡|무겁|가볍|길|짧|크|늦|빠|느|강|약|굵|얇)야|[가-힣]+은야', '오탈자(형용사+야)'),
    # 단어 붙여쓰기 (조사 뒤 바로 다음 단어 붙음 — 보다는신, 매수보다는신 등)
    (r'[가-힣]{2,}[는은을를이가][가-힣]{2,}(?=[가-힣])', '단어 붙여쓰기'),
    # 불완전 서술어 (더 + 목적어만 있고 서술어 없음 — 더 선택을, 더 생각을 등)
    (r'더\s+[가-힣]{2,}[을를](?:\s|[.,!?]|$)', '불완전 서술어'),
    # 외국어 혼입 (한자·일본어·아랍어·키릴·태국어 — 기존 라틴확장과 별도)
    (r'[\u3040-\u30ff]',   '일본어 혼입'),
    (r'[\u0600-\u06ff]',   '아랍어 혼입'),
    (r'[\u0400-\u04ff]',   '키릴 혼입'),
    (r'[\u0e00-\u0e7f]',   '태국어 혼입'),
]

_SENT_STOP = {
    "을","를","이","가","의","은","는","에","도","와","과","로","으로",
    "그","및","등","이다","있다","하다","됩니다","합니다","했다","있어",
    "하는","한다","된다","했어","이야","거야","이에","따라","위해",
}

_TOPIC_STOP = {
    "을","를","이","가","의","은","는","에","도","와","과","로","으로","그","및","등","관련",
}

# ── 고유명사 교정 딕셔너리 ─────────────────────────────────────
_PROPER_NOUNS = {
    "앤스로픽":  "앤트로픽",
    "클로드":    "Claude",
    "챗지피티":  "ChatGPT",
    "챗 지피티": "ChatGPT",
    "오픈에이아이": "OpenAI",
    "오픈 에이아이": "OpenAI",
    "메타버스":  "메타버스",   # 정확 표기 유지용
    "구글 딥마인드": "Google DeepMind",
    "딥마인드":  "DeepMind",
    "제미나이":  "Gemini",
    "젬마":      "Gemma",
    "마이크로소프트": "Microsoft",
    "아이폰":    "iPhone",
    "아이패드":  "iPad",
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


def _fix_proper_nouns(text: str) -> str:
    """고유명사 오표기 자동 교정"""
    for wrong, correct in _PROPER_NOUNS.items():
        text = text.replace(wrong, correct)
    return text


def _get_first_sentence(text: str) -> str:
    """카드 본문에서 첫 문장 추출 (이모지 포함 첫 줄)"""
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # 첫 문장 부호까지만
        m = re.search(r'^.+?[.!?]', line)
        return m.group() if m else line[:80]
    return ""


def _intro_overlap(a: str, b: str) -> float:
    """두 첫 문장의 토큰 겹침 비율"""
    ta = _sent_tokens(re.sub(r'[^\w\s]', '', a))
    tb = _sent_tokens(re.sub(r'[^\w\s]', '', b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


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
    prior_intros: list | None = None,
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

    # 5. 도입부 유사도 (이전 카드들과 첫 문장 비교)
    if prior_intros:
        my_intro = _get_first_sentence(text)
        for prev in prior_intros:
            sim = _intro_overlap(my_intro, prev)
            if sim >= 0.7:
                issues.append(f"도입부 유사 (겹침 {sim:.0%}): '{prev[:30]}'")
                hints.append(
                    f"⚠️ 도입부 표현이 앞 카드와 {sim:.0%} 겹침. 완전히 다른 방식으로 시작해야 함.\n"
                    f"   금지된 도입 패턴: {', '.join(repr(p[:30]) for p in prior_intros)}\n"
                    "   새로운 각도의 첫 문장: 반전 사실·짧은 팩트·솔직한 의문 등 다양하게."
                )
                break  # 하나만 찾으면 충분

    # 6. 반복 문장 (블로그만)
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
    prior_intros: list | None = None,
    max_retries: int = 2,
) -> tuple:
    """
    텍스트 생성 후 quality_check를 통과할 때까지 재생성.
    자동 교정(해시태그 위치, 에디터 구조)은 매 시도마다 적용.

    Returns: (text: str, retry_count: int, encountered_issues: list)
    """
    def _autofix(t: str) -> str:
        t = _fix_hashtag_position(t)
        t = _fix_proper_nouns(t)
        if is_blog:
            t = _enforce_editor_structure(t)
        return t

    all_issues: list = []   # 학습용 — 모든 시도에서 발생한 이슈 누적

    # 초기 생성
    text = ask_gemini(prompt, system=SYSTEM, temperature=temperature, max_tokens=max_tokens)
    if is_blog:
        text = _ensure_complete(text, prompt)
    text = _autofix(text)
    result = quality_check(text, headline, check_repetition=check_repetition, prior_intros=prior_intros)

    if result["passed"]:
        return text, 0, []

    all_issues.extend(result["issues"])

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
        result = quality_check(text, headline, check_repetition=check_repetition, prior_intros=prior_intros)
        if result["passed"]:
            print(f"  ✅ [{label}] {attempt}회 재생성 후 품질 통과")
            return text, attempt, all_issues   # 재시도했지만 통과 → 이슈는 학습용으로 반환
        all_issues.extend(result["issues"])

    print(f"  ⚠️  [{label}] {max_retries}회 재생성 후에도 미통과 {result['issues']} — 그대로 사용")
    return text, max_retries, all_issues


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════

def run(brief: dict) -> dict:
    print("✍️  작가 에이전트 실행 중...")
    quality_log = []  # (label, retry_count, issues)

    # 최근 7일 학습 힌트 로드
    from utils.quality_tracker import get_adaptive_hints, record_run
    adaptive_hints = get_adaptive_hints(days=7)
    if adaptive_hints:
        print("  📚 학습 힌트 적용 중 (최근 반복 실패 항목 주의)")


    # ── 카드뉴스 ───────────────────────────────────────────────
    captions = []
    prior_intros: list[str] = []   # 이전 카드들의 첫 문장 누적

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

        # 이전 카드 도입부 힌트 (2번째 카드부터)
        prior_intro_note = ""
        if prior_intros:
            prior_intro_note = (
                "\n⚠️ 아래 도입부는 이미 앞 카드에서 사용됨 — 이 카드의 첫 문장은 완전히 다른 방식으로 시작할 것:\n"
                + "\n".join(f'  - "{s}"' for s in prior_intros)
                + "\n"
            )

        reader_insight = item.get("reader_insight", "")
        # reader_insight가 없어도 항상 힌트 포함 — 없으면 직접 뽑도록 지시
        if reader_insight.strip():
            insight_note = f"\n독자 인사이트 (반드시 반영): {reader_insight}\n"
        else:
            insight_note = "\n💡 시아아빠 한 줄은 반드시 직접 뽑을 것 — 독자가 이 뉴스를 읽고 당장 뭘 해야 하거나 어떻게 생각이 바뀌어야 하는지 날카롭게 1문장.\n"

        prompt = f"""인스타그램 카드뉴스 캡션 써줘. 주제: "{item['headline']}"
{facts_note}{insight_note}
각도: {item['angle']}
톤: {item['tone']}
{prior_intro_note}{adaptive_hints}
[글 구조 — 레이블 없이 내용만 바로 써]
① 이모지 1개 + 스크롤 멈추게 하는 첫 문장 (한 줄). 이모지 없으면 실패.
  - 솔직한 반응·반전 사실·짧은 팩트로 시작. 질문으로만 시작하지 마.
  - "와 이거 실화야" / "오늘 이 뉴스 보고 좀 멈칫했어" / "오늘 아침 뉴스 보다가 멈칫했어" 절대 금지.
  - 카드마다 완전히 다른 방식으로 시작. 앞 카드와 같은 패턴 반복 금지.
  - 예시: "숫자 하나가 눈에 박혔어." / "이거 생각보다 진짜 큰 변화야." / "이 수치 보고 두 번 읽었어." / "딱 한 줄로 요약하면 이래." / "솔직히 이건 예상 못 했어." / "이 뉴스, 제목만 보면 별거 아닌 것 같은데."
② 배경 1~2문장 + 핵심 사실 2~3줄. 구체적 수치·이름·날짜 포함. 추상적 묘사 금지.
③ 💡 시아아빠 한 줄: [내용] — ⚠️ 이 줄은 반드시 출력. 없으면 실패.
  - "그래서 나한테 뭔 의미야?"에 답하는 문장.
  - 독자가 이 카드를 읽고 얻어가야 할 핵심 관점 or 행동 포인트.
  - "~해야겠다", "~를 생각해봐야 할 것 같아" 같은 공허한 마무리 금지.
  - 구체적이고 날카롭게. 예: "지금 변동금리 대출 있으면 이번 주 안에 한 번 확인해봐."
  - 반드시 "💡 시아아빠 한 줄: " 접두어로 시작하고 마침표로 끝낼 것.

⛔ 절대 금지 — 아래 중 하나라도 쓰면 실패:
- "와 이거 실화야", "와 이 ~는", "와 이거" 로 시작하는 모든 문장
- 구조 레이블 출력: "첫 줄:", "그 다음:", "마지막:" 등 ①②③ 구조 레이블 직접 출력 (단, "💡 시아아빠 한 줄:" 접두어는 반드시 출력해야 함 — 이건 예외)
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

본문(해시태그 제외) 150~260자. 글 다 쓴 뒤 빈 줄 두 개 → 해시태그 8개를 한 줄에. 해시태그는 반드시 #단어 형식 (빈 # 금지). 해시태그를 본문 사이에 넣으면 실패.
"""
        caption, retries, issues = _generate_with_quality(
            prompt, item["headline"], label,
            max_tokens=1200, temperature=0.7,
            prior_intros=prior_intros if prior_intros else None,
        )
        quality_log.append((label, retries, issues))

        # ── 💡 시아아빠 한 줄 누락 자동 보완 ──────────────────
        if "시아아빠 한 줄" not in caption and "💡" not in caption:
            print(f"  ⚠️  [{label}] 💡 시아아빠 한 줄 누락 — 자동 보완 시도")
            patch_prompt = f"""아래 카드뉴스 캡션에 "💡 시아아빠 한 줄"이 빠져 있어.
캡션:
{caption}

이 캡션에 맞는 "💡 시아아빠 한 줄"을 딱 한 줄만 써줘.
반드시 "💡 시아아빠 한 줄: " 으로 시작하고 마침표로 끝낼 것.
공허한 마무리("~해야겠다", "~바뀔 것 같다") 금지. 구체적이고 날카롭게."""
            patch = ask_gemini(patch_prompt, system=SYSTEM, temperature=0.7, max_tokens=150)
            if patch and "💡" in patch:
                patch = patch.strip().split("\n")[0]  # 첫 줄만
                # 해시태그 앞에 삽입
                tag_idx = caption.find("\n#")
                if tag_idx >= 0:
                    caption = caption[:tag_idx].rstrip() + "\n\n" + patch + "\n" + caption[tag_idx:].lstrip("\n")
                else:
                    caption = caption.rstrip() + "\n\n" + patch
                print(f"  ✅  [{label}] 자동 보완 완료")

        # 이 카드의 첫 문장을 누적 (다음 카드 비교용)
        first = _get_first_sentence(caption)
        if first:
            prior_intros.append(first)

        # 카드 간 주제 중복 감지 — 로그만 (planner 단에서 수정 필요)
        for prev in captions:
            overlap = _topic_overlap(item["headline"], prev["headline"])
            if overlap >= 0.7:
                print(
                    f"  ⚠️  [{label}] 주제 중복 경고 ({overlap:.0%})"
                    f" — '{prev['headline'][:30]}'와 유사 (planner 점검 필요)"
                )

        # 제목 앞 쉼표·마침표·특수문자 자동 제거
        clean_headline = re.sub(r'^[,.\s!?·•]+', '', item["headline"]).strip()

        captions.append({
            "headline":    clean_headline,
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
{facts_block}{adaptive_hints}
이걸 주제로 블로그 글 한 편 써줘.

핵심 포인트: {', '.join(b['main_points'])}

⚠️ 이 주제 하나에만 집중해. 다른 뉴스 절대 섞지 마.

[목적] 독자가 이 글 읽고 "아, 이 뉴스가 나한테 이런 의미구나"를 가져가야 해.
       단순 요약이 아니라 — 시아아빠의 해석과 관점이 있는 opinion piece.

[시작 — 매번 달라야 함, 절대 "멈칫했어"·"놀랐어" 패턴 반복 금지]
  뉴스 봤을 때의 솔직한 첫 반응 or 핵심 팩트 직격으로 시작. 인사말·서론 금지.
  매번 다른 방식으로 시작할 것:
  예) "숫자 하나가 눈에 박혔어." / "솔직히 이건 예상 못 했어." /
      "이 뉴스, 제목만 보면 별거 아닌 것 같은데..." / "딱 한 줄로 요약하면 이래."
  ❌ 절대 금지: "오늘 이 뉴스 보고 좀 멈칫했어", "오늘 아침 뉴스 보다가 멈칫했어"

[흐름] 도입(첫 반응 + 핵심 팩트) → ## 소제목1(왜 이게 지금 터졌나) → ## 소제목2(우리 삶·돈에 직접 연결) → ## 소제목3(그래서 뭘 봐야 하나)

[소제목 규칙] ## 3개. 반드시 대화체 질문·감탄·단언 형식.
  ✅ 예: "## 근데 왜 하필 지금이야?" / "## 이게 내 지갑이랑 무슨 상관이야?" / "## 앞으로 뭘 눈여겨봐야 해?"
  ❌ 금지: "배경", "내용", "의미", "영향", "분석", "결론" 같은 단어로만 이뤄진 소제목

[각 섹션 작성 규칙]
- 각 ## 아래 문단: 2~3문장씩, 문장 사이 줄바꿈 포함
- 2문장마다 한 번씩 줄바꿈 — 덩어리 텍스트 금지
- 구체적 수치·기업명·날짜 반드시 포함
- 이전 섹션 내용 재진술·요약 금지

[마무리] 마지막 섹션의 마지막 문장: 독자가 당장 할 수 있는 것 or 눈여겨볼 신호 — 날카롭고 구체적으로.
  ❌ 금지: "~를 바랍니다", "지켜봐야겠다", "어떻게 될지 궁금하다" 같은 공허한 마무리

⛔ 절대 금지:
- "오늘 이 뉴스 보고 좀 멈칫했어" / "오늘 아침 뉴스 보다가 멈칫했어" (시작 문장 패턴 반복)
- "와 이거 실화야", "이러한", "이처럼", "이를 통해", "~에 큰 영향을 미칠", "~로 보인다"
- 동일한 주어+서술어 조합 2회 이상
- 긴 문단 뭉치기 — 반드시 2~3문장마다 줄바꿈
- 한글 단어를 한자로 혼용 / 한국어·영어 외 외국어
- 없는 수치·사실 창작

분량 1400~1800자. 각 ## 섹션당 300~400자. 마지막 문장은 마침표로.
글 다 쓰고 빈 줄 두 개 뒤에 해시태그 8개. 해시태그는 반드시 #단어 형식 (빈 # 금지).
"""
    article = ""
    try:
        article, retries, issues = _generate_with_quality(
            blog_prompt, b["title"], "블로그",
            max_tokens=2000, temperature=0.88,
            is_blog=True, check_repetition=True,
        )
        quality_log.append(("블로그", retries, issues))
        print(f"  ✅ 블로그 아티클 완성 ({len(article)}자, 재생성 {retries}회)")
    except Exception as e:
        quality_log.append(("블로그", 0, []))
        print(f"  ⚠️  블로그 아티클 실패 (카드뉴스는 유지): {e}")

    # ── 품질 요약 로그 ─────────────────────────────────────────
    total_retries = sum(r for _, r, _ in quality_log)
    regen_items = [(l, r) for l, r, _ in quality_log if r > 0]
    if regen_items:
        detail = ", ".join(f"{l}:{r}회" for l, r in regen_items)
        print(f"\n  📊 품질 요약: 총 재생성 {total_retries}회 — {detail}")
    else:
        print(f"\n  📊 품질 요약: 전체 품질 통과 (재생성 0회)")

    # ── 품질 학습 기록 저장 ───────────────────────────────────
    try:
        from datetime import date as _date
        record_run(_date.today().strftime("%Y-%m-%d"), quality_log)
    except Exception as e:
        print(f"  ⚠️  품질 학습 기록 실패 (무시): {e}")

    # ── 자기 반성 & 성장 학습 ────────────────────────────────────
    try:
        from utils.agent_memory import (add_diary, get_persona, get_diary,
                                        should_update_persona, update_persona)
        total_retries = sum(r for _, r, _ in quality_log)
        issues_seen   = list({iss for _, _, issues in quality_log for iss in issues})

        # ── 출력 품질 자동 점검 (💡 시아아빠 한 줄 누락 감지) ──────
        missing_insight = [
            c["headline"][:20] for c in captions
            if "시아아빠 한 줄" not in c.get("caption","") and "💡" not in c.get("caption","")
        ]
        if missing_insight:
            issues_seen.append(f"💡누락:{len(missing_insight)}건")
            print(f"  ⚠️  품질 점검: 💡 시아아빠 한 줄 누락 {len(missing_insight)}건 — {missing_insight}")

        persona       = get_persona("이작가")
        recent        = " / ".join(e["lesson"][:25] for e in get_diary("이작가", 2)) or "첫 날"
        ctx = (f"카드뉴스 {len(captions)}개 + 블로그 작성. "
               f"재생성 {total_retries}회. "
               + (f"문제: {issues_seen[:2]}" if issues_seen else "품질 이슈 없음"))

        lesson_raw = ask_gemini(
            f"너는 카드뉴스 작가 '이작가'야.\n"
            f"지금까지 나: {persona[:60]}\n최근 메모: {recent}\n오늘 한 일: {ctx}\n\n"
            "오늘 글 쓰면서 느끼거나 배운 점 1문장. 1인칭 반말, 50자 이내.",
            temperature=0.85, max_tokens=80,
        )
        lesson = lesson_raw.strip().split("\n")[0][:150]
        if lesson:
            add_diary("이작가", lesson, trigger="daily_write")
            print(f"  📝 이작가 오늘의 학습: {lesson[:45]}")

        if should_update_persona("이작가"):
            diary_str = "\n".join(f"- {e['lesson']}" for e in get_diary("이작가", 7))
            new_p = ask_gemini(
                f"너는 카드뉴스 작가 '이작가'야.\n지금까지 나: {persona}\n"
                f"최근 학습 일기:\n{diary_str}\n\n"
                "이 경험을 바탕으로 지금의 나를 2문장으로. 1인칭 반말, 70자 이내.",
                temperature=0.8, max_tokens=120,
            ).strip().split("\n")[0][:300]
            if new_p:
                update_persona("이작가", new_p)
                print("  ✨ 이작가 페르소나 진화 완료")
    except Exception as e:
        print(f"  ⚠️  이작가 자기 반성 실패 (무시): {e}")

    return {"captions": captions, "article": article, "blog_title": b["title"]}
