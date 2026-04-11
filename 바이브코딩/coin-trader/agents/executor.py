import os
from utils.bithumb_client import (
    get_krw_balance, get_coin_balance, get_current_price,
    buy_market_order, sell_market_order,
)

MAX_INVEST = float(os.getenv("MAX_INVEST_KRW", "80000"))
MIN_ORDER  = 5000   # 빗썸 최소 주문금액


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
        t = holding["ticker"]
        # 항상 API에서 실제 잔고 조회 — state.json 추정값과 실제 체결량 차이로 인한 5600 방지
        qty = get_coin_balance(t)
        if qty <= 0:
            print(f"  ⚠️  {t} 실제 잔고 없음 → 스킵")
            return None
        print(f"  💰 실제 잔고: {qty:.8f}개 (state: {holding.get('qty', 0):.8f}개)")
        # 빗썸 시장가 매도 최소금액 체크 (qty × 현재가 >= 5000)
        price = get_current_price(t)
        sell_value = qty * price
        if sell_value < 5000:
            print(f"  ⚠️  매도 금액 {sell_value:,.0f}원 < 5,000원 최소 기준 — 매도 보류 (가격 회복 대기)")
            return holding
        result = sell_market_order(t, qty)
        pct = round((price / holding["buy_price"] - 1) * 100, 2) if holding.get("buy_price") else 0
        print(f"  ✅ 매도 완료: {t} | 수익률 {pct:+.2f}%")
        return None

    if verb == "BUY":
        if holding:
            # 이미 다른 종목 보유 중 — 먼저 매도 후 매수
            print(f"  🔄 기존 보유({holding['ticker']}) 매도 후 신규 매수")
            # 항상 API에서 실제 잔고 조회 — state.json 추정값과 다를 수 있음
            qty = get_coin_balance(holding["ticker"])
            # 기존 보유 매도 전에도 최소금액 체크
            price_chk = get_current_price(holding["ticker"])
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
        invest = krw * 0.92   # 보유 KRW 기준 — 수수료 + 슬리피지 + API 오차 여유 포함

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
