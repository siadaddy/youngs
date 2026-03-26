import os, re
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

# 항상 모든 프롬프트에 붙이는 언어 규칙
_LANG_RULE = "\n\n[언어 규칙] 반드시 한국어와 영어, 이모지만 사용하세요. 한자·중국어·일본어·아랍어 등 다른 문자는 절대 사용하지 마세요."


def _sanitize(text: str) -> str:
    """한자·외계어 등 불필요한 문자 제거 및 정리"""
    # CJK 통합 한자 (중국어 한자): U+4E00–U+9FFF
    text = re.sub('\u4e00-\u9fff'.join(['[', ']']), '', text)
    # CJK Extension A (U+3400–U+4DBF)
    text = re.sub('\u3400-\u4dbf'.join(['[', ']']), '', text)
    # 아랍어 (U+0600–U+06FF)
    text = re.sub('\u0600-\u06ff'.join(['[', ']']), '', text)
    # 태국어 (U+0E00–U+0E7F)
    text = re.sub('\u0e00-\u0e7f'.join(['[', ']']), '', text)
    # 연속 공백 → 단일 공백
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # 3줄 이상 빈 줄 → 2줄
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def ask_gemini(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Groq API 호출 (함수명은 하위 호환 유지)"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system + _LANG_RULE})
    messages.append({"role": "user", "content": prompt})

    r = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    r.raise_for_status()
    result = r.json()["choices"][0]["message"]["content"].strip()
    return _sanitize(result)
