import os, re, itertools
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_KEYS = [
    k for k in [
        os.getenv("GROQ_API_KEY"),
        os.getenv("GROQ_API_KEY_2"),
        os.getenv("GROQ_API_KEY_3"),
        os.getenv("GROQ_API_KEY_4"),
    ] if k
]
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"   # 컨텍스트 크기용 — Groq 폴백에서만 사용

# 라운드로빈 이터레이터 (모듈 로드 시 한 번만 생성)
_key_cycle = itertools.cycle(range(len(GROQ_KEYS))) if GROQ_KEYS else iter([])

_LANG_RULE = (
    "\n\n[언어 규칙] 반드시 한국어와 영어, 이모지만 사용하세요. "
    "한자·일본어·아랍어·힌디어·러시아어·베트남어·태국어 등 "
    "한국어·영어가 아닌 모든 문자는 절대 사용하지 마세요. "
    "특히 한글 단어를 한자로 표기하거나 혼용하는 것 절대 금지 — "
    "'차량(車輛)', '금전(金錢)', '車량', '金錢적인' 같은 표현 금지. 한글로만 쓰세요. "
    "독일어·프랑스어 등 외국어 단어도 금지입니다. "
    "모르는 사실은 절대 지어내지 마세요 — 불확실하면 '~로 알려졌다', '~에 따르면' 등 표현을 쓰세요."
)


def _sanitize(text: str) -> str:
    text = re.sub(r'[\u4e00-\u9fff]', '', text)
    text = re.sub(r'[\u3400-\u4dbf]', '', text)
    text = re.sub(r'[\U00020000-\U0002A6DF]', '', text)
    text = re.sub(r'[\u3040-\u309f]', '', text)
    text = re.sub(r'[\u30a0-\u30ff]', '', text)
    text = re.sub(r'[\u0600-\u06ff]', '', text)
    text = re.sub(r'[\u0e00-\u0e7f]', '', text)
    text = re.sub(r'[\u0400-\u04ff]', '', text)
    text = re.sub(r'[\u0900-\u097f]', '', text)
    text = re.sub(r'[\u1e00-\u1eff]', '', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


_429_models: set = set()  # 이번 세션에서 429 발생한 모델 — 이후 호출에서 스킵


def _call_gemini(prompt: str, system: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
    """Gemini API 직접 호출 — 2.5-flash 우선, 2.0-flash는 429 미발생 시에만 시도"""
    import time
    gemini_keys = [k for k in [os.getenv("GEMINI_API_KEY", ""), os.getenv("GEMINI_API_KEY_2", "")] if k]
    if not gemini_keys:
        raise RuntimeError("GEMINI_API_KEY 없음")

    gemini_models = ["gemini-2.5-flash", "gemini-2.0-flash"]

    for key_idx, gemini_key in enumerate(gemini_keys):
        key_label = f"키{key_idx + 1}"
        for model_idx, gmodel in enumerate(gemini_models):
            if gmodel in _429_models:
                continue  # 이번 세션에서 이미 429난 모델 스킵
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gmodel}:generateContent?key={gemini_key}"
            if system:
                payload = {
                    "system_instruction": {"parts": [{"text": system + _LANG_RULE}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": temperature, "maxOutputTokens": max(max_tokens, 8192)},
                }
            else:
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": temperature, "maxOutputTokens": max(max_tokens, 8192)},
                }
            if json_mode:
                payload["generationConfig"]["responseMimeType"] = "application/json"

            for attempt in range(1, 4):
                try:
                    r = requests.post(url, json=payload, timeout=60)
                    r.raise_for_status()
                    result = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if key_idx > 0 or model_idx > 0 or attempt > 1:
                        print(f"  ✅ Gemini {key_label}/{gmodel} 성공" + (f" (시도 {attempt})" if attempt > 1 else ""))
                    return _sanitize(result)
                except Exception as e:
                    status = getattr(getattr(e, 'response', None), 'status_code', 0)
                    print(f"  ⚠️  Gemini {key_label}/{gmodel} 시도 {attempt}/3 실패: {e}")
                    if status == 429:
                        _429_models.add(gmodel)
                        print(f"      429 → {gmodel} 이번 세션 스킵 처리, 다음 모델로 전환...")
                        break
                    if attempt < 3:
                        print(f"      15초 대기 후 재시도...")
                        time.sleep(15)

            if model_idx < len(gemini_models) - 1:
                active = [m for m in gemini_models[model_idx+1:] if m not in _429_models]
                if active:
                    print(f"  ⏳ Gemini {key_label}/{gmodel} 실패 → {active[0]}...")

        if key_idx < len(gemini_keys) - 1:
            print(f"  ⏳ Gemini {key_label} 소진 → 키{key_idx + 2}로 전환...")

    raise RuntimeError("Gemini 모든 키/모델 실패")


def _call_groq(prompt: str, system: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
    """Groq API 호출 — 라운드로빈 키 분배, 폴백용"""
    import time

    messages = []
    if system:
        messages.append({"role": "system", "content": system + _LANG_RULE})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    if not GROQ_KEYS:
        raise RuntimeError("GROQ API 키 없음")

    start_idx = next(_key_cycle)
    key_order = [GROQ_KEYS[(start_idx + i) % len(GROQ_KEYS)] for i in range(len(GROQ_KEYS))]
    last_r = None

    for key_idx, api_key in enumerate(key_order):
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        key_label = f"키{(start_idx + key_idx) % len(GROQ_KEYS) + 1}"

        for attempt in range(1, 3):   # 키당 최대 2회 시도
            try:
                r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)
                last_r = r
            except Exception as conn_err:
                print(f"  ⚠️  Groq {key_label} 연결 오류: {conn_err}")
                break

            if r.status_code == 413:
                # 프롬프트가 너무 큼 — 다른 키 시도해도 동일하므로 즉시 포기
                print(f"  ⚡ Groq {key_label} 413 프롬프트 초과 — Groq 폴백 불가")
                raise RuntimeError("Groq 413: 프롬프트가 너무 큼 — Gemini만 사용 가능")
            if r.status_code == 429:
                print(f"  ⚡ Groq {key_label} 429 → 다음 키 전환...")
                break

            r.raise_for_status()
            result = r.json()["choices"][0]["message"]["content"].strip()
            print(f"  ✅ Groq {key_label} 폴백 성공")
            return _sanitize(result)

        if key_idx < len(key_order) - 1:
            print(f"  ⚠️  Groq {key_label} 소진 → 다음 키...")

    if last_r is not None:
        last_r.raise_for_status()
    raise RuntimeError("Groq 모든 키 소진")


def ask_gemini(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 4096, json_mode: bool = False) -> str:
    """Gemini 우선 호출 → 실패 시 Groq 폴백
    뉴스레터처럼 프롬프트가 큰 작업에 Gemini가 적합 (TPM 100만, 대형 컨텍스트)
    """
    # 1순위: Gemini
    try:
        return _call_gemini(prompt, system, temperature, max_tokens, json_mode)
    except Exception as e:
        print(f"  ⚠️  Gemini 전체 실패 ({e}) → Groq 폴백 시도...")

    # 2순위: Groq 폴백
    try:
        return _call_groq(prompt, system, temperature, max_tokens, json_mode)
    except Exception as e:
        raise RuntimeError(f"Gemini + Groq 모두 실패: {e}")


def ask_ai(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 2048, json_mode: bool = False) -> str:
    """2.5-flash 우선 (2.0-flash 스킵) → 실패 시 Groq 폴백. weekly_trend 등 단발성 호출용."""
    return ask_gemini25_first(prompt, system=system, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)


def ask_groq_first(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 2048, json_mode: bool = False) -> str:
    """Groq 우선 호출 → 실패 시 Gemini 폴백"""
    try:
        result = _call_groq(prompt, system, temperature, max_tokens, json_mode)
        print(f"  ✅ Groq 성공")
        return result
    except Exception as e:
        print(f"  ⚠️  Groq 전체 실패 ({e}) → Gemini 폴백 시도...")
    try:
        return _call_gemini(prompt, system, temperature, max_tokens, json_mode)
    except Exception as e:
        raise RuntimeError(f"Groq + Gemini 모두 실패: {e}")


def ask_gemini25_first(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 2048, json_mode: bool = False) -> str:
    """Gemini 2.5-flash 우선 (2.0-flash 스킵) → 실패 시 Groq 폴백
    음악 큐레이터처럼 반복 호출이 많은 작업용.
    2.0-flash는 RPM 429가 일상적이므로 처음부터 건너뜀.
    """
    import time

    gemini_keys = [k for k in [os.getenv("GEMINI_API_KEY", ""), os.getenv("GEMINI_API_KEY_2", "")] if k]

    # 1순위: Gemini 2.5-flash (키1 → 키2)
    for key_idx, gemini_key in enumerate(gemini_keys):
        key_label = f"키{key_idx + 1}"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max(max_tokens, 2048)},
        }
        if system:
            payload["system_instruction"] = {"parts": [{"text": system}]}
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        for attempt in range(1, 3):   # 키당 최대 2회
            try:
                r = requests.post(url, json=payload, timeout=60)
                r.raise_for_status()
                result = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"  ✅ Gemini 2.5-flash {key_label} 성공")
                return _sanitize(result)
            except Exception as e:
                status = getattr(getattr(e, 'response', None), 'status_code', 0)
                print(f"  ⚠️  Gemini 2.5-flash {key_label} 시도 {attempt}/2 실패: {status or e}")
                if attempt < 2:
                    wait = 30 if status == 429 else 10
                    print(f"      {wait}초 대기 후 재시도...")
                    time.sleep(wait)

        if key_idx < len(gemini_keys) - 1:
            print(f"  ⏳ Gemini 2.5-flash {key_label} 실패 → 키{key_idx + 2}로 전환...")

    print(f"  ⚠️  Gemini 2.5-flash 전체 실패 → Groq 폴백...")

    # 2순위: Groq 폴백
    try:
        result = _call_groq(prompt, system, temperature, max_tokens, json_mode)
        print(f"  ✅ Groq 폴백 성공")
        return result
    except Exception as e:
        raise RuntimeError(f"Gemini 2.5-flash + Groq 모두 실패: {e}")
