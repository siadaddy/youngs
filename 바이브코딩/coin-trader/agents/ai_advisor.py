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
GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

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
    """Groq 전부 실패 시 Gemini 폴백"""
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY 없음")
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300},
    }
    r = requests.post(f"{GEMINI_URL}?key={GEMINI_KEY}", json=payload, timeout=30)
    r.raise_for_status()
    return _sanitize(r.json()["candidates"][0]["content"]["parts"][0]["text"].strip())


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
        if d.get("vb"):   s += 2   # 변동성 돌파 보너스
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
30분봉 기준 스윙 매매 봇입니다. 빗썸 수수료 0.25%(왕복 0.5%)를 고려해 수익 가능성 높은 신호에만 진입하세요.

⚠️ 손절(-{stop_loss}%)·익절은 시스템 코드가 자동 처리합니다. AI는 수익률 숫자를 기준으로 손절 판단 절대 금지.

1. 보유 중이면 HOLD 또는 SELL만 선택 가능
2. 미보유 중이면 BUY(종목 지정) 또는 HOLD만 선택 가능
3. 【VB 매수 — 최우선】미보유 시 VB✅ + 점수 +3 이상 → BUY (변동성 돌파는 가장 검증된 신호)
4. 【강한 매수】미보유 시 점수 +5 이상 + ADX 25 이상(추세O) → BUY 적극 고려
5. ADX 15 미만 + VB❌ 종목은 BUY 금지 — 방향성 없음
   거래량 변화 -30% 이하인 종목, 현재가 500원 미만 소형 코인은 BUY 금지 — 유동성 부족 위험
6. 【매도】보유 종목 기술 점수 -2 이하 이거나, RSI 70 이상 + MACD 하락/데드크로스 → SELL
7. 【기회 교체 — 신중하게】아래 조건 모두 충족 시에만 교체 허용 (reason에 "기회 교체" 명시):
   - 매수 후 최소 60분 경과
   - 보유 종목 수익률 -2% 미만
   - 보유 종목 기술 점수 -1 이하
   - 다른 종목 점수 +5 이상 + ADX 25 이상 또는 VB✅ + 점수 +4 이상
8. 보유 종목 수익률 -2% 이상이면 무조건 HOLD — 섣부른 교체 금지
9. 보유 종목 수익률 +3% 이상이면 수익 보호 우선, 교체 절대 금지
10. 뚜렷한 신호 없으면 HOLD

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
