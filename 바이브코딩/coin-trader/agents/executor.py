import os
from utils.upbit_client import (
    get_krw_balance, get_coin_balance, get_current_price,
    buy_market_order, sell_market_order,
)

MAX_INVEST = float(os.getenv("MAX_INVEST_KRW", "80000"))
MIN_ORDER  = 4500   # 업비트 최소 주문금액(5000) - 손실 후 잔고 부족 방지용 여유


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
        qty = holding.get("qty", 0)
        if qty <= 0:
            qty = get_coin_balance(t)
        if qty <= 0:
            print(f"  ⚠️  {t} 잔고 없음 → 스킵")
            return None
        result = sell_market_order(t, qty)
        price = get_current_price(t)
        pct = round((price / holding["buy_price"] - 1) * 100, 2) if holding.get("buy_price") else 0
        print(f"  ✅ 매도 완료: {t} | 수익률 {pct:+.2f}%")
        return None

    if verb == "BUY":
        if holding:
            # 이미 다른 종목 보유 중 — 먼저 매도 후 매수
            print(f"  🔄 기존 보유({holding['ticker']}) 매도 후 신규 매수")
            qty = holding.get("qty", 0) or get_coin_balance(holding["ticker"])
            if qty > 0:
                sell_market_order(holding["ticker"], qty)

        krw = get_krw_balance()
        if krw < MIN_ORDER:
            print(f"  ⚠️  KRW 잔고 부족 ({krw:,.0f}원) — BUY 스킵")
            return None
        invest = min(krw, MAX_INVEST)  # 업비트가 수수료 내부 처리 — 정확히 5,000원 전달해야 최소주문 충족

        result = buy_market_order(ticker, invest)
        price = get_current_price(ticker)
        qty = invest / price if price else 0

        print(f"  ✅ 매수 완료: {ticker} | {invest:,.0f}원 | 단가 {price:,.0f}원")
        return {
            "ticker": ticker,
            "buy_price": price,
            "qty": qty,
            "invest_krw": invest,
        }

    return holding
