import os, re, json, time, requests
from dotenv import load_dotenv


def _sanitize(text: str) -> str:
    text = re.sub(r'[\u4e00-\u9fff]', '', text)   # CJK 한자
    text = re.sub(r'[\u3040-\u30ff]', '', text)   # 히라가나·가타카나
    text = re.sub(r'[\u0600-\u06ff]', '', text)   # 아랍어
    text = re.sub(r'[\u0400-\u04ff]', '', text)   # 키릴
    return text.strip()

load_dotenv()

GROQ_KEYS    = [k for k in [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2"), os.getenv("GROQ_API_KEY_3"), os.getenv("GROQ_API_KEY_4")] if k]
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"
GEMINI_KEYS  = [k for k in [os.getenv("GEMINI_API_KEY", ""), os.getenv("GEMINI_API_KEY_2", "")] if k]
GEMINI_MODELS = ["gemini-2.0-flash", "gemini-2.5-flash"]

SYSTEM = """당신은 10년 경력의 암호화폐 퀀트 트레이더입니다.
기술적 지표(RSI, MACD, 볼린저밴드)를 기반으로 냉정하게 매매 판단을 내립니다.
감정 없이 데이터만 보고, 반드시 JSON 형식으로만 응답합니다.
한국어로 reason을 작성합니다."""


def _ask_groq(prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ]
    payload = {"model": GROQ_MODEL, "messages": messages, "temperature": 0.3, "max_tokens": 300}

    for key_idx, api_key in enumerate(GROQ_KEYS):
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        for attempt in range(1, 4):
            r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
            if r.status_code == 429:
                if key_idx < len(GROQ_KEYS) - 1:
                    print(f"  ⚠️  Groq 키{key_idx+1} 429 → 즉시 키{key_idx+2}로 전환")
                    break
                wait = min(int(r.headers.get("retry-after", 10)), 20)
                print(f"  ⏳ Groq 키{key_idx+1}(마지막) 속도 제한 — {wait}초 대기 ({attempt}/3)...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return _sanitize(r.json()["choices"][0]["message"]["content"].strip())
        else:
            if key_idx < len(GROQ_KEYS) - 1:
                print(f"  ⚠️  Groq 키{key_idx+1} 소진 → 키{key_idx+2}로 전환...")

    raise RuntimeError("모든 Groq API 키 소진")


def _ask_gemini(prompt: str) -> str:
    """Groq 전부 실패 시 Gemini 폴백 — 키1→키2, 각 키에서 2.0-flash→2.5-flash"""
    if not GEMINI_KEYS:
        raise RuntimeError("GEMINI_API_KEY 없음")
    payload_base = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300},
    }
    for key_idx, gemini_key in enumerate(GEMINI_KEYS):
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
            for attempt in range(1, 4):
                try:
                    r = requests.post(url, json=payload_base, timeout=30)
                    r.raise_for_status()
                    return _sanitize(r.json()["candidates"][0]["content"]["parts"][0]["text"].strip())
                except Exception as e:
                    status = getattr(getattr(e, 'response', None), 'status_code', 0)
                    wait = 65 if status == 429 else 10
                    print(f"  ⚠️  Gemini 키{key_idx+1}/{model} 시도 {attempt} 실패: {e}")
                    if attempt < 3:
                        time.sleep(wait)
        if key_idx < len(GEMINI_KEYS) - 1:
            print(f"  ⏳ Gemini 키{key_idx+1} 소진 → 키{key_idx+2}로 전환...")
    raise RuntimeError("Gemini 모든 키/모델 실패")


def _ask_llm(prompt: str) -> str:
    """Groq 우선, 실패 시 Gemini 폴백"""
    try:
        return _ask_groq(prompt)
    except Exception as e:
        print(f"  ⚠️  Groq 전체 실패 ({e}) → Gemini 폴백 시도...")
        result = _ask_gemini(prompt)
        print("  ✅ Gemini 폴백 성공")
        return result


def run(market_data: list, holding: dict | None, cooldown_tickers: list | None = None) -> dict:
    """
    market_data: analyzer.run() 결과 리스트
    holding: {"ticker": "KRW-BTC", "buy_price": 120000000, "qty": 0.0001} 또는 None

    반환: {"action": "BUY"|"SELL"|"HOLD", "ticker": "KRW-XXX"|None, "reason": "..."}
    """
    print("🤖 AI 어드바이저 실행 중...")

    # 보유 현황 텍스트
    def _fmt_price(p: float) -> str:
        """1원 미만 소수점 코인도 정확하게 표시"""
        if p >= 100:   return f"{p:,.0f}원"
        if p >= 1:     return f"{p:,.2f}원"
        if p >= 0.01:  return f"{p:.4f}원"
        return f"{p:.6f}원"

    if holding:
        from utils.bithumb_client import get_current_price
        now_price = get_current_price(holding["ticker"])
        pct = round((now_price / holding["buy_price"] - 1) * 100, 2) if holding["buy_price"] else 0
        holding_text = (
            f"현재 보유: {holding['ticker']} | "
            f"매수가 {_fmt_price(holding['buy_price'])} | "
            f"현재가 {_fmt_price(now_price)} | "
            f"수익률 {pct:+.2f}%"
        )
    else:
        holding_text = "현재 보유 종목 없음"

    # 종목 분석 텍스트 + 스코어 계산 (상위 15개만 — 토큰 절약)
    def _score(d: dict) -> int:
        s = 0
        rsi = d.get("rsi", 50)
        # RSI 스코어링 — 극단적 과매도(< 20)는 급락 추세일 수 있어 중립 처리
        if 20 <= rsi < 35:   s += 2   # 과매도 반등 구간 (매수 적합)
        elif rsi < 20:       s += 0   # 극단적 과매도 = 급락 중일 수 있음 → 중립
        elif rsi < 50:       s += 1   # 중립 하단
        elif rsi > 75:       s -= 2   # 과매수
        elif rsi > 65:       s -= 1   # 과매수 진입
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
        # VB 보너스 — 거래량 증가 동반 시에만 신뢰
        vol = d.get("vol_change_pct", 0)
        if d.get("vb") and vol >= 20:   s += 2   # VB + 거래량 급증 → 강한 신호
        elif d.get("vb"):               s += 1   # VB만 → 약한 신호 (이전 +2에서 약화)
        return s

    scored = []
    for d in market_data[:15]:
        score = _score(d)
        scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)

    # 상위 5개 분석 결과 로그 출력 (디버깅용)
    print("  📊 상위 5개 종목:")
    for score, d in scored[:5]:
        adx = d.get("adx", 0)
        vb_str = "VB✅" if d.get("vb") else "VB❌"
        print(f"    {d['ticker']} | 점수:{score:+d} | RSI {d['rsi']} | {d['macd']} | {d['bb']} | ADX {adx} | {vb_str}")

    rows = []
    for score, d in scored:
        adx = d.get("adx", 0)
        trend = "추세O" if adx >= 15 else "횡보"
        vol_str = f"거래량{d['vol_change_pct']:+.0f}%"
        vb_str = "VB✅" if d.get("vb") else "VB❌"
        rows.append(
            f"- {d['ticker']} | 현재가 {d['price']:,.0f}원 | "
            f"RSI {d['rsi']} | MACD {d['macd']} | BB {d['bb']} | {vol_str} | ADX {adx}({trend}) | {vb_str} | 점수:{score:+d}"
        )
    market_text = "\n".join(rows)

    stop_loss = float(os.getenv("STOP_LOSS_PCT", "5.0"))

    # 최소 보유 시간 계산 (기회 교체 방지용)
    hold_minutes = 0
    if holding and holding.get("buy_time"):
        try:
            from datetime import datetime as _dt
            buy_dt = _dt.strptime(holding["buy_time"], "%Y-%m-%d %H:%M")
            hold_minutes = int((_dt.now() - buy_dt).total_seconds() / 60)
        except Exception:
            pass
    hold_info = f"(매수 후 {hold_minutes}분 경과)" if holding else ""

    # 재진입 쿨다운 종목 텍스트
    cooldown_text = ""
    if cooldown_tickers:
        cooldown_text = f"\n【⛔ 재진입 금지 종목 (손절 후 쿨다운 중)】\n{', '.join(cooldown_tickers)}\n위 종목은 BUY 절대 금지 — 쿨다운 해제까지 진입 금지.\n"

    prompt = f"""【현재 포트폴리오】
{holding_text} {hold_info}

【KRW 시장 상위 종목 분석 (30분봉 + 변동성돌파 기준)】
{market_text}
{cooldown_text}
【판단 규칙】
30분봉 단기 매매 봇입니다. 투자금 5만원, 빗썸 수수료 0.25%(왕복 0.5%) 고려해 손익비 유리한 신호에만 진입.
목표: 빠른 진입/청산, 죽은 포지션 오래 들고 있지 않기.

⚠️ 손절(-{stop_loss}%)·익절·트레일링스탑·시간초과 청산은 시스템이 자동 처리. AI는 수익률 수치로 손절 판단 금지.

【매수 규칙】
1. 미보유 시에만 BUY 가능
2. USDT, USDC, DAI, BUSD, TUSD, FDUSD 등 스테이블코인 → BUY 절대 금지
3. RSI < 20 → BUY 금지 (급락 추세 중 — 반등 신호 아님)
4. VB✅ + 거래량 변화 +20% 이상 + 점수 +4 이상 → BUY 최우선 (강한 돌파 신호)
5. 점수 +5 이상 + ADX 25 이상 + MACD 골든크로스 또는 상승 → BUY 적극 고려
6. ADX 20 미만 + VB❌ → BUY 금지 (방향성 없음, 기준 강화)
7. 거래량 변화 -30% 이하 → BUY 금지 (거래 참여자 없음)

【매도/HOLD 규칙 — 보유 시간에 따라 기준 완화】
8. 보유 4시간 미만: 기술 점수 -3 이하 또는 RSI 72+ + MACD 데드크로스 → SELL
9. 보유 4~6시간: 기술 점수 -1 이하 또는 RSI 70+ + MACD 하락 → SELL 적극 고려
10. 보유 6시간 이상 + 수익률 0% 이하: 뚜렷한 반등 신호 없으면 SELL (죽은 포지션)
11. 보유 시간과 무관하게 RSI 75+ + MACD 데드크로스 → SELL

【기회 교체 — 매우 신중하게】
12. 매수 후 90분 이상 + 보유 수익률 -3% 미만 + 보유 점수 -2 이하
    + 다른 종목 점수 +5 이상 + ADX 25 이상 + VB✅ + 거래량 +20% 이상 → SELL 후 BUY (reason에 "기회 교체" 명시)
13. 보유 수익률 -1% 이상이면 교체 금지 (손실 확정 최소화)
14. 보유 수익률 +2% 이상 → 교체 절대 금지, 수익 보호
15. 뚜렷한 신호 없으면 HOLD

반드시 아래 JSON만 출력하세요 (다른 텍스트 없이):
{{"action": "BUY" | "SELL" | "HOLD", "ticker": "BTC" 또는 "XRP" 등 코인심볼만 (KRW- 접두어 없이), "reason": "한국어로 판단 이유 2~3문장"}}"""

    raw = _ask_llm(prompt)

    # JSON 추출 — raw_decode로 첫 번째 JSON 객체만 파싱 (Extra data 오류 방지)
    raw = raw.replace("```json", "").replace("```", "").strip()
    start = raw.find('{')
    if start == -1:
        print(f"  ⚠️  AI 응답에서 JSON 추출 실패 → HOLD 폴백: {raw[:100]}")
        return {"action": "HOLD", "ticker": None, "reason": "AI 응답 파싱 실패 — HOLD 유지"}

    try:
        result, _ = json.JSONDecoder().raw_decode(raw, start)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON 파싱 오류 → HOLD 폴백: {e}")
        return {"action": "HOLD", "ticker": None, "reason": "AI JSON 파싱 오류 — HOLD 유지"}

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
