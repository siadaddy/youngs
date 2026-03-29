import os, re, json, time, requests
from dotenv import load_dotenv


def _sanitize(text: str) -> str:
    text = re.sub(r'[\u4e00-\u9fff]', '', text)   # CJK 한자
    text = re.sub(r'[\u3040-\u30ff]', '', text)   # 히라가나·가타카나
    text = re.sub(r'[\u0600-\u06ff]', '', text)   # 아랍어
    text = re.sub(r'[\u0400-\u04ff]', '', text)   # 키릴
    return text.strip()

load_dotenv()

GROQ_KEYS = [k for k in [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2")] if k]
GROQ_URL  = "https://api.groq.com/openai/v1/chat/completions"
MODEL     = "llama-3.3-70b-versatile"

SYSTEM = """당신은 10년 경력의 암호화폐 퀀트 트레이더입니다.
기술적 지표(RSI, MACD, 볼린저밴드)를 기반으로 냉정하게 매매 판단을 내립니다.
감정 없이 데이터만 보고, 반드시 JSON 형식으로만 응답합니다.
한국어로 reason을 작성합니다."""


def _ask_groq(prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ]
    payload = {"model": MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 300}

    for key_idx, api_key in enumerate(GROQ_KEYS):
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        for attempt in range(1, 4):
            r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
            if r.status_code == 429:
                wait = min(int(r.headers.get("retry-after", 30)) + 5, 90)
                print(f"  ⏳ Groq 키{key_idx+1} 속도 제한 — {wait}초 대기 ({attempt}/3)...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return _sanitize(r.json()["choices"][0]["message"]["content"].strip())
        if key_idx < len(GROQ_KEYS) - 1:
            print(f"  ⚠️  Groq 키{key_idx+1} 소진 → 키{key_idx+2}로 전환...")

    raise RuntimeError("모든 Groq API 키 소진")


def run(market_data: list, holding: dict | None) -> dict:
    """
    market_data: analyzer.run() 결과 리스트
    holding: {"ticker": "KRW-BTC", "buy_price": 120000000, "qty": 0.0001} 또는 None

    반환: {"action": "BUY"|"SELL"|"HOLD", "ticker": "KRW-XXX"|None, "reason": "..."}
    """
    print("🤖 AI 어드바이저 실행 중...")

    # 보유 현황 텍스트
    if holding:
        from utils.upbit_client import get_current_price
        now_price = get_current_price(holding["ticker"])
        pct = round((now_price / holding["buy_price"] - 1) * 100, 2) if holding["buy_price"] else 0
        holding_text = (
            f"현재 보유: {holding['ticker']} | "
            f"매수가 {holding['buy_price']:,.0f}원 | "
            f"현재가 {now_price:,.0f}원 | "
            f"수익률 {pct:+.2f}%"
        )
    else:
        holding_text = "현재 보유 종목 없음"

    # 종목 분석 텍스트 + 스코어 계산 (상위 15개만 — 토큰 절약)
    def _score(d: dict) -> int:
        s = 0
        rsi = d.get("rsi", 50)
        if rsi < 35:    s += 2
        elif rsi < 45:  s += 1
        elif rsi > 65:  s -= 1
        elif rsi > 75:  s -= 2
        macd = d.get("macd", "")
        if "골든크로스" in macd:   s += 2
        elif "상승" in macd:       s += 1
        elif "데드크로스" in macd:  s -= 2
        elif "하락" in macd:       s -= 1
        bb = d.get("bb", "")
        if "하단" in bb:    s += 2
        elif "중하단" in bb: s += 1
        elif "상단" in bb:  s -= 2
        elif "중상단" in bb: s -= 1
        return s

    rows = []
    for d in market_data[:15]:
        score = _score(d)
        adx = d.get("adx", 0)
        trend = "추세O" if adx >= 20 else "횡보"
        vol_str = f"거래량{d['vol_change_pct']:+.0f}%"
        rows.append(
            f"- {d['ticker']} | 현재가 {d['price']:,.0f}원 | "
            f"RSI {d['rsi']} | MACD {d['macd']} | BB {d['bb']} | {vol_str} | ADX {adx}({trend}) | 점수:{score:+d}"
        )
    market_text = "\n".join(rows)

    stop_loss = float(os.getenv("STOP_LOSS_PCT", "5.0"))

    prompt = f"""【현재 포트폴리오】
{holding_text}

【KRW 시장 상위 종목 분석 (4시간봉 기준)】
{market_text}

【판단 규칙 — 스코어 기반】
각 종목의 점수(RSI·MACD·BB 합산)와 ADX 추세 여부를 기준으로 판단하세요.

1. 보유 중이면 HOLD 또는 SELL만 선택 가능
2. 미보유 중이면 BUY(종목 지정) 또는 HOLD만 선택 가능
3. 수익률이 -{stop_loss}% 이하면 반드시 SELL (손절)
4. 【강한 매도】보유 종목 점수 -2 이하 + RSI 65 이상 + MACD 데드크로스 → SELL
5. 【강한 매수】미보유 시 점수 +4 이상 + ADX 20 이상(추세O) → BUY 적극 고려
6. 【중간 매수】미보유 시 점수 +3 이상 + ADX 20 이상 + 거래량 +50% 이상 → BUY 고려
7. ADX 20 미만(횡보) 종목은 점수가 높아도 BUY 금지 — 가짜 신호 가능성 높음
8. 【기회 교체】보유 종목 수익률 -3%~+3% 횡보 + 보유 종목 점수 0 이하,
   다른 종목 점수 +4 이상 + ADX 20 이상 + 거래량 +50% 이상 → SELL 후 교체 (reason에 "기회 교체" 명시)
9. 뚜렷한 신호 없으면 HOLD

반드시 아래 JSON만 출력하세요 (다른 텍스트 없이):
{{"action": "BUY" | "SELL" | "HOLD", "ticker": "KRW-XXX" 또는 null, "reason": "한국어로 판단 이유 2~3문장"}}"""

    raw = _ask_groq(prompt)

    # JSON 추출
    raw = raw.replace("```json", "").replace("```", "").strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not match:
        raise ValueError(f"AI 응답에서 JSON 추출 실패: {raw[:200]}")

    result = json.loads(match.group())

    # 필드 검증
    action = result.get("action", "HOLD").upper()
    if action not in ("BUY", "SELL", "HOLD"):
        action = "HOLD"
    result["action"] = action

    if action == "BUY" and not result.get("ticker"):
        result["action"] = "HOLD"
        result["reason"] = "BUY 판단이나 ticker 없음 → HOLD로 변경"

    print(f"  ✅ AI 판단: {result['action']} {result.get('ticker') or ''}")
    print(f"  💬 이유: {result.get('reason', '')}")
    return result
