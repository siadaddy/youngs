import json, re, html
from utils.gemini_client import ask_gemini

_PLAN_STOP = {
    '의','을','를','이','가','은','는','에','도','와','과','로','으로',
    '그','및','등','관련','대한','위한','따른','하는','하고','하여',
    '했다','한다','있다','있어','됐다','통해','위해','대해',
}

def _title_overlap(t1: str, t2: str) -> float:
    def kw(s):
        return {w for w in re.sub(r'[^\w\s]', '', s).split()
                if len(w) > 1 and w not in _PLAN_STOP}
    ka, kb = kw(t1), kw(t2)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / min(len(ka), len(kb))

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
        # 전체 후보 수집
        candidates = []
        for cat, articles in newsletter_data["categorized"].items():
            for a in articles[:ARTICLE_PER_CAT]:
                candidates.append((cat, a))

        # 유사 제목 중복 제거 (70% 이상 겹치면 첫 번째만 유지)
        DEDUP_THR = 0.7
        deduped, seen_titles = [], []
        for cat, a in candidates:
            title = html.unescape(a.get("title", ""))
            if any(_title_overlap(title, t) >= DEDUP_THR for t in seen_titles):
                continue
            deduped.append((cat, a))
            seen_titles.append(title)

        removed = len(candidates) - len(deduped)
        if removed:
            print(f"  🔍 중복 기사 {removed}건 제거 (유사도 ≥{int(DEDUP_THR*100)}%)")

        lines = []
        for cat, a in deduped:
            title   = html.unescape(a.get("title", ""))
            link    = a.get("link", "")
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
- instagram[0]: 반드시 자동차/모빌리티/전기차/수소차/자동차부품/자동차금융 관련 뉴스여야 함. 동물/사건사고/연예/스포츠는 절대 금지. 해당 카테고리 뉴스가 없으면 자동차 업계 전반 트렌드 각도로 접근. 이 규칙은 예외 없이 적용
- 5개 카드는 반드시 서로 다른 사건/인물/기업을 다뤄야 함. 같은 사건을 다른 각도로 쓰는 것도 중복으로 간주하고 하나만 선택.
  예) '미군 이란 항구 봉쇄' + '미국 이란 긴장 고조' → 같은 사건, 하나만 / '테슬라 실적 부진' + '테슬라 주가 하락' → 같은 기업 같은 맥락, 하나만
  5개 각각이 완전히 다른 주제여야 독자가 다양한 정보를 얻을 수 있음
- 제외: 범죄, 연예인 사생활, 정치 편향, 미검증 루머
- 제외: 시군구 단위 지자체 소식, 복지/행사 안내, 특정 중소기업 단순 홍보 — 전국·국제 단위 임팩트 없는 뉴스는 선택 금지
- 제외: 의료/제약 단순 정책 뉴스 (급여 고시, 보험 적용 범위, 특정 약품 허가 등) — 자동차·경제·IT·국제 관련성 없는 경우
- instagram 5개 중 경제/산업/기술/국제 뉴스 최소 3개 이상 포함 필수
- blog title: "뉴스레터 요약", "오늘의 뉴스", "뉴스 브리프", "4월 X일" 같은 날짜·요약성 제목 금지
- blog는 반드시 단일 뉴스 하나에만 집중 — main_points 3개 모두 같은 사건에 대한 것
- blog main_points는 "배경 → 내용 → 의미/영향" 구조로 작성
- blog 주제 선정 우선순위: 국제 정치/경제 이슈 > 국내 산업/기술 > 일반 사회. 소규모 기업 해외 진출, 지역 소식, 지자체 행사 등 임팩트 작은 뉴스는 blog 주제로 금지
- blog source_facts: 해당 주제 하나에 대한 구체적 사실만. 다른 뉴스 내용 혼합 금지
- source_facts는 반드시 50자 이상의 구체적 사실로 작성. "없음", "해당없음", "정보없음" 입력 금지
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

    # instagram[0] 자동차 주제 검증 — 자동차 키워드 없으면 swap 또는 강제 재생성
    _CAR_KW = {
        '자동차','차량','전기차','수소차','모빌리티','BMW','현대차','기아','테슬라',
        '벤츠','아우디','폭스바겐','토요타','혼다','EV','하이브리드','자율주행','충전',
        '배터리','내연기관','SUV','세단','트럭','부품','딜러','출고','리콜','카셰어링',
        '모터쇼','자동차금융','할부','카풀','완성차','카니발','팰리세이드','아이오닉',
        '제네시스','포르쉐','람보르기니','페라리','닛산','쉐보레','지프','포드',
    }
    _CAR_BANNED = {'동물','늑대','곰','호랑이','뱀','연예','스포츠','야구','축구','농구','배구'}

    def _is_car(item: dict) -> bool:
        text = (item.get('headline','') + item.get('angle','') + str(item.get('keywords',[])))
        return any(kw in text for kw in _CAR_KW)

    instagram = brief.get("instagram", [])
    if instagram and not _is_car(instagram[0]):
        # 나머지 카드 중 자동차 관련 찾아서 swap
        swap_idx = next((i for i, it in enumerate(instagram[1:], 1) if _is_car(it)), None)
        if swap_idx:
            print(f"  ⚠️  instagram[0] 자동차 무관 → 카드{swap_idx+1}과 swap")
            instagram[0], instagram[swap_idx] = instagram[swap_idx], instagram[0]
        else:
            # 자동차 카드가 아예 없으면 instagram[0] 강제 재생성
            print("  ⚠️  instagram[0] 자동차 무관 + 대체 없음 → 강제 재생성")
            car_prompt = f"""아래 뉴스에서 자동차/모빌리티/전기차/수소차 관련 기사 하나를 골라 카드뉴스 브리프 JSON을 작성하세요.
반드시 자동차 관련 뉴스여야 합니다. 동물·사건사고·연예·스포츠는 절대 금지.

=== 원문 뉴스 ===
{article_list_text if article_list_text else newsletter_text}

출력 형식 (JSON 객체만):
{{"headline":"...","angle":"...","keywords":[...],"tone":"...","source_facts":"실제 뉴스 내용에서 뽑은 구체적 사실 3~4문장 (수치·이름·날짜 포함, 최소 80자)","source_url":"...","source_name":"..."}}"""
            try:
                import time as _time; _time.sleep(3)
                raw_car = ask_gemini(car_prompt, system=SYSTEM, temperature=0.5, json_mode=True, max_tokens=600)
                raw_car = raw_car.replace("```json","").replace("```","").strip()
                car_item = json.loads(raw_car)
                if _is_car(car_item):
                    brief["instagram"][0] = car_item
                    print("  ✅ instagram[0] 자동차 카드 재생성 완료")
                else:
                    print("  ⚠️  재생성 후에도 자동차 무관 — 원본 유지")
            except Exception as e:
                print(f"  ⚠️  instagram[0] 재생성 실패: {e}")

    # source_facts 할루시네이션 방지 — 부실 카드 재생성
    _INVALID_FACTS = {"없음", "해당없음", "정보없음", "해당 없음", "정보 없음"}
    regenerated = 0
    for idx, item in enumerate(brief.get("instagram", [])):
        facts = str(item.get("source_facts", "")).strip()
        need_regen = (
            len(facts) < 50
            or any(kw in facts for kw in _INVALID_FACTS)
        )
        if not need_regen:
            continue
        print(f"  ⚠️  카드{idx+1} source_facts 부실({len(facts)}자) → 단일 재생성...")
        single_prompt = f"""아래 뉴스 기사에서 카드뉴스 브리프 1개만 JSON으로 작성하세요.

=== 원문 뉴스 ===
{article_list_text if article_list_text else newsletter_text}

대상 카드:
headline: {item.get('headline')}
angle: {item.get('angle')}

출력 형식 (JSON 객체만):
{{"headline":"...","angle":"...","keywords":[...],"tone":"...","source_facts":"실제 뉴스 내용에서 뽑은 구체적 사실 3~4문장 (수치·이름·날짜 포함, 최소 80자)","source_url":"...","source_name":"..."}}

source_facts는 반드시 80자 이상의 구체적 내용으로 작성. "없음" 금지."""
        try:
            import time as _time; _time.sleep(3)
            raw2 = ask_gemini(single_prompt, system=SYSTEM, temperature=0.65, json_mode=True, max_tokens=600)
            raw2 = raw2.replace("```json","").replace("```","").strip()
            patched = json.loads(raw2)
            if len(str(patched.get("source_facts","")).strip()) >= 50:
                brief["instagram"][idx] = patched
                regenerated += 1
                print(f"  ✅ 카드{idx+1} source_facts 재생성 완료")
            else:
                print(f"  ⚠️  카드{idx+1} 재생성 후에도 부실 — 원본 유지")
        except Exception as e:
            print(f"  ⚠️  카드{idx+1} 재생성 실패: {e}")

    total = len(brief['instagram'])
    regen_note = f" (source_facts 재생성 {regenerated}건)" if regenerated else ""
    print(f"  ✅ 인스타 {total}개, 블로그 1개 브리프 완성{regen_note}")
    return brief
