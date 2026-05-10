import os
from utils.bithumb_client import (
    get_krw_balance, get_coin_balance, get_current_price,
    buy_market_order, sell_market_order,
)
from utils.blacklist import is_blacklisted

MAX_INVEST   = float(os.getenv("MAX_INVEST_KRW", "50000"))  # 10만→5만
MIN_ORDER    = 5000   # 빗썸 최소 주문금액
STABLECOINS  = {"USDT", "USDC", "DAI", "BUSD", "TUSD", "USDD", "FDUSD", "USDP"}  # 매수 절대 금지


def run(action: dict, holding: dict | None) -> dict:
    """
    action: ai_advisor.run() 결과
    holding: 현재 보유 상태 또는 None

    반환: 갱신된 holding 상태 (None이면 미보유)
    """
    verb = action["action"]
    ticker = action.get("ticker")

    if verb == "HOLD":
        print("  ⏸  HOLD — 포지션 유지")
        return holding

    if verb == "SELL":
        if not holding:
            print("  ⚠️  SELL 지시 but 보유 종목 없음 → 스킵")
            return None
        # force=True: 손절/트레일링/강제청산 — 최소금액 체크 무시하고 반드시 매도
        force = action.get("force", False)
        t = holding["ticker"]
        # 실제 잔고 조회 (API 오류 시 최대 3회 재시도)
        qty = -1.0
        for _attempt in range(3):
            qty = get_coin_balance(t)
            if qty >= 0:
                break
            import time as _t; _t.sleep(2)
        if qty < 0:
            # API 오류(-1.0) — state.json qty 폴백으로 매도 시도
            fallback_qty = holding.get("qty", 0)
            print(f"  ⚠️  {t} 잔고 조회 API 오류 → state.json 폴백 수량 {fallback_qty:.8f}개 사용")
            if fallback_qty <= 0:
                print(f"  ⚠️  state.json에도 수량 없음 → holding 클리어")
                return None
            qty = fallback_qty
        elif qty == 0:
            print(f"  ⚠️  {t} 실제 잔고 없음 (이미 매도됨) → holding 클리어")
            return None
        else:
            print(f"  💰 실제 잔고: {qty:.8f}개 (state: {holding.get('qty', 0):.8f}개)")
        # 현재가 조회 — 0이면 API 오류로 보고 SELL 보류
        price = get_current_price(t)
        if price <= 0:
            print(f"  ⚠️  {t} 현재가 0원 (API 오류) — SELL 보류, holding 유지")
            return holding
        # 빗썸 시장가 매도 최소금액 체크 (qty × 현재가 >= 5000)
        # force=True(손절/강제청산)면 최소금액 무시 — 가격이 충분히 떨어지면 영원히 못 파는 상황 방지
        sell_value = qty * price
        if sell_value < 5000 and not force:
            print(f"  ⚠️  매도 금액 {sell_value:,.0f}원 < 5,000원 최소 기준 — 매도 보류 (가격 회복 대기)")
            return holding
        elif sell_value < 5000 and force:
            print(f"  ⚠️  매도 금액 {sell_value:,.0f}원 < 5,000원 but force=True — 강제 매도 실행")
        result = sell_market_order(t, qty)
        pct = round((price / holding["buy_price"] - 1) * 100, 2) if holding.get("buy_price") else 0
        print(f"  ✅ 매도 완료: {t} | 수익률 {pct:+.2f}%")
        return None

    if verb == "BUY":
        # 스테이블코인 하드 차단 — AI 프롬프트 무시해도 여기서 막음
        coin_upper = (ticker or "").replace("KRW-", "").upper()
        if coin_upper in STABLECOINS:
            print(f"  🚫 스테이블코인 BUY 차단: {coin_upper} → HOLD 유지")
            return holding

        # 블랙리스트 하드 차단 — 분석 단계에서 제외됐어도 이중 확인
        if is_blacklisted(coin_upper):
            print(f"  🚫 블랙리스트 BUY 차단: {coin_upper} (반복 손절 학습) → HOLD 유지")
            return holding

        if holding:
            # 이미 다른 종목 보유 중 — 먼저 매도 후 매수
            print(f"  🔄 기존 보유({holding['ticker']}) 매도 후 신규 매수")
            # 항상 API에서 실제 잔고 조회 — state.json 추정값과 다를 수 있음
            qty = get_coin_balance(holding["ticker"])
            if qty < 0:
                qty = holding.get("qty", 0)
                print(f"  ⚠️  기존 보유 잔고 API 오류 → state.json 폴백 {qty:.8f}개")
            # 기존 보유 매도 전에도 최소금액 체크
            price_chk = get_current_price(holding["ticker"])
            if price_chk <= 0:
                print(f"  ⚠️  기존 보유 현재가 조회 실패 — 교체 취소, HOLD 유지")
                return holding
            if qty > 0 and qty * price_chk >= 5000:
                sell_market_order(holding["ticker"], qty)
            elif qty > 0:
                print(f"  ⚠️  기존 보유 매도 금액 {qty * price_chk:,.0f}원 < 5,000원 — 교체 취소, HOLD 유지")
                return holding
            else:
                print(f"  ⚠️  기존 보유 실제 잔고 없음 — 매도 스킵 후 매수 진행")

        krw = get_krw_balance()
        if krw < MIN_ORDER:
            print(f"  ⚠️  KRW 잔고 부족 ({krw:,.0f}원) — BUY 스킵")
            return None
        invest = min(krw, MAX_INVEST) * 0.997  # MAX_INVEST 한도 내에서 수수료(0.25%) 여유만

        result = buy_market_order(ticker, invest)
        price = get_current_price(ticker)

        # 실제 체결 수량 API에서 조회 (추정값 대신 정확한 값 저장)
        import time as _time
        _time.sleep(1)  # 체결 반영 대기
        actual_qty = get_coin_balance(ticker)
        qty = actual_qty if actual_qty > 0 else (invest / price if price else 0)

        from datetime import datetime
        print(f"  ✅ 매수 완료: {ticker} | {invest:,.0f}원 | 단가 {price:,.0f}원 | 실제수량 {qty:.8f}개")
        return {
            "ticker": ticker,
            "buy_price": price,
            "qty": qty,
            "invest_krw": invest,
            "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    return holding
