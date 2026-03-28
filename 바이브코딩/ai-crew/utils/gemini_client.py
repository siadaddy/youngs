import os, re
import requests
from dotenv import load_dotenv

load_dotenv()

# 키 1이 일일 쿼터 소진되면 키 2로 자동 전환
GROQ_KEYS = [
    k for k in [
        os.getenv("GROQ_API_KEY"),
        os.getenv("GROQ_API_KEY_2"),
    ] if k
]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

_LANG_RULE = "\n\n[언어 규칙] 반드시 한국어와 영어, 이모지만 사용하세요. 한자·중국어·일본어·아랍어 등 다른 문자는 절대 사용하지 마세요."


def _sanitize(text: str) -> str:
    text = re.sub('[\u4e00-\u9fff]', '', text)
    text = re.sub('[\u3400-\u4dbf]', '', text)
    text = re.sub('[\u0600-\u06ff]', '', text)
    text = re.sub('[\u0e00-\u0e7f]', '', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def ask_gemini(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Groq API 호출 — 키 2개 폴백 + 429 자동 대기"""
    import time

    messages = []
    if system:
        messages.append({"role": "system", "content": system + _LANG_RULE})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for key_idx, api_key in enumerate(GROQ_KEYS):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        key_label = f"키{key_idx + 1}"

        for attempt in range(1, 5):
            r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=60)

            if r.status_code == 429:
                retry_after = int(r.headers.get("retry-after", 30))
                wait = min(retry_after + 5, 90)
                print(f"  ⏳ Groq {key_label} 속도 제한 — {wait}초 대기 후 재시도 ({attempt}/4)...")
                time.sleep(wait)
                continue

            r.raise_for_status()
            result = r.json()["choices"][0]["message"]["content"].strip()
            if key_idx > 0:
                print(f"  ✅ Groq {key_label}로 성공")
            return _sanitize(result)

        # 이 키로 4회 모두 실패 → 다음 키 시도
        if key_idx < len(GROQ_KEYS) - 1:
            print(f"  ⚠️  Groq {key_label} 쿼터 소진 → 키{key_idx + 2}로 전환...")

    # 모든 키 소진
    r.raise_for_status()
