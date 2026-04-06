import os
import pybithumb
from dotenv import load_dotenv

load_dotenv()

_bithumb = None

def get_bithumb():
    """인증된 Bithumb 인스턴스 반환 (DRY_RUN=true면 None)"""
    global _bithumb
    if os.getenv("DRY_RUN", "true").lower() == "true":
        return None
    if _bithumb is None:
        access = os.getenv("BITHUMB_ACCESS_KEY", "")
        secret = os.getenv("BITHUMB_SECRET_KEY", "")
        if not access or not secret:
            raise ValueError("BITHUMB_ACCESS_KEY / BITHUMB_SECRET_KEY 없음 — .env 확인")
        _bithumb = pybithumb.Bithumb(access, secret)
    return _bithumb


def get_krw_balance() -> float:
    """보유 KRW 잔고 반환"""
    b = get_bithumb()
    if b is None:
        return float(os.getenv("MAX_INVEST_KRW", "80000")) * 2  # dry run 가상 잔고
    # get_balance(coin) → (보유코인, 사용중코인, 보유원화, 사용중원화)
    result = b.get_balance("BTC")
    if isinstance(result, tuple) and len(result) >= 3:
        return float(result[2])  # total_krw
    return 0.0


def get_coin_balance(ticker: str) -> float:
    """보유 코인 수량 반환. ticker = 'BTC' 형식"""
    b = get_bithumb()
    coin = ticker.replace("KRW-", "")  # 혹시 KRW- 형식이 넘어와도 처리
    if b is None:
        return 0.0
    result = b.get_balance(coin)
    if isinstance(result, tuple) and len(result) >= 1:
        return float(result[0])  # total_coin
    return 0.0


def get_current_price(ticker: str) -> float:
    """현재가 조회 — 연결 오류 시 2회 재시도. ticker = 'BTC' 또는 'KRW-BTC' 모두 허용"""
    import time
    coin = ticker.replace("KRW-", "")
    for attempt in range(3):
        try:
            price = pybithumb.get_current_price(coin)
            return float(price) if price else 0.0
        except Exception:
            if attempt < 2:
                time.sleep(5)
    return 0.0


def get_krw_tickers() -> list:
    """KRW 마켓 전체 티커 목록 — 'BTC', 'ETH' 형식으로 반환"""
    import time
    for attempt in range(3):
        try:
            return pybithumb.get_tickers(payment_currency="KRW")
        except Exception:
            if attempt < 2:
                time.sleep(5)
    return []


def buy_market_order(ticker: str, amount_krw: float) -> dict:
    """시장가 매수. DRY_RUN이면 시뮬레이션.
    pybithumb buy_market_order는 코인 수량을 받으므로 KRW → 수량 변환 후 주문"""
    coin = ticker.replace("KRW-", "")
    price = get_current_price(coin)
    if not price:
        raise RuntimeError(f"현재가 조회 실패 — 매수 취소 (ticker={coin})")
    qty = amount_krw / price

    b = get_bithumb()
    if b is None:
        print(f"  [DRY RUN] 매수 시뮬레이션: {coin} {qty:.6f}개 @ {price:,.0f}원 ({amount_krw:,.0f}원)")
        return {"ticker": coin, "price": price, "qty": qty, "dry_run": True}
    result = b.buy_market_order(coin, qty)
    if result is None:
        raise RuntimeError(f"매수 주문 실패 — 잔고 부족 또는 API 오류 (ticker={coin}, amount={amount_krw:,.0f}원)")
    if isinstance(result, dict) and result.get("status") not in (None, "0000"):
        raise RuntimeError(f"매수 주문 거부 — {result} (ticker={coin}, amount={amount_krw:,.0f}원)")
    return result


def sell_market_order(ticker: str, qty: float) -> dict:
    """시장가 매도. DRY_RUN이면 시뮬레이션"""
    coin = ticker.replace("KRW-", "")
    b = get_bithumb()
    if b is None:
        price = get_current_price(coin)
        print(f"  [DRY RUN] 매도 시뮬레이션: {coin} {qty:.8f}개 @ {price:,.0f}원")
        return {"ticker": coin, "price": price, "qty": qty, "dry_run": True}
    result = b.sell_market_order(coin, qty)
    if result is None:
        raise RuntimeError(f"매도 주문 실패 — API 오류 (ticker={coin}, qty={qty:.8f})")
    if isinstance(result, dict) and result.get("status") not in (None, "0000"):
        raise RuntimeError(f"매도 주문 거부 — {result} (ticker={coin}, qty={qty:.8f})")
    return result
