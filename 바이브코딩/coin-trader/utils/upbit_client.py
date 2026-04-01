import os
import pyupbit
from dotenv import load_dotenv

load_dotenv()

_upbit = None

def get_upbit():
    """인증된 Upbit 인스턴스 반환 (DRY_RUN=true면 None)"""
    global _upbit
    if os.getenv("DRY_RUN", "true").lower() == "true":
        return None
    if _upbit is None:
        access = os.getenv("UPBIT_ACCESS_KEY", "")
        secret = os.getenv("UPBIT_SECRET_KEY", "")
        if not access or not secret:
            raise ValueError("UPBIT_ACCESS_KEY / UPBIT_SECRET_KEY 없음 — .env 확인")
        _upbit = pyupbit.Upbit(access, secret)
    return _upbit


def get_krw_balance() -> float:
    """보유 KRW 잔고 반환"""
    upbit = get_upbit()
    if upbit is None:
        return float(os.getenv("MAX_INVEST_KRW", "80000")) * 2  # dry run 가상 잔고
    balance = upbit.get_balance("KRW")
    return float(balance) if balance else 0.0


def get_coin_balance(ticker: str) -> float:
    """보유 코인 수량 반환. ticker = 'KRW-BTC' → 'BTC'만 추출"""
    upbit = get_upbit()
    coin = ticker.replace("KRW-", "")
    if upbit is None:
        return 0.0
    balance = upbit.get_balance(coin)
    return float(balance) if balance else 0.0


def get_current_price(ticker: str) -> float:
    """현재가 조회 (인증 불필요)"""
    price = pyupbit.get_current_price(ticker)
    return float(price) if price else 0.0


def get_krw_tickers() -> list:
    """KRW 마켓 전체 티커 목록"""
    return pyupbit.get_tickers(fiat="KRW")


def buy_market_order(ticker: str, amount_krw: float) -> dict:
    """시장가 매수. DRY_RUN이면 시뮬레이션"""
    upbit = get_upbit()
    if upbit is None:
        print(f"  [DRY RUN] 매수 시뮬레이션: {ticker} {amount_krw:,.0f}원")
        price = get_current_price(ticker)
        qty = amount_krw / price if price else 0
        return {"ticker": ticker, "price": price, "qty": qty, "dry_run": True}
    result = upbit.buy_market_order(ticker, amount_krw)
    if result is None:
        raise RuntimeError(f"매수 주문 실패 — 잔고 부족 또는 API 오류 (ticker={ticker}, amount={amount_krw:,.0f}원)")
    if isinstance(result, dict) and "error" in result:
        raise RuntimeError(f"매수 주문 거부 — {result['error']} (ticker={ticker}, amount={amount_krw:,.0f}원)")
    return result


def sell_market_order(ticker: str, qty: float) -> dict:
    """시장가 매도. DRY_RUN이면 시뮬레이션"""
    upbit = get_upbit()
    if upbit is None:
        price = get_current_price(ticker)
        print(f"  [DRY RUN] 매도 시뮬레이션: {ticker} {qty:.8f}개 @ {price:,.0f}원")
        return {"ticker": ticker, "price": price, "qty": qty, "dry_run": True}
    result = upbit.sell_market_order(ticker, qty)
    if result is None:
        raise RuntimeError(f"매도 주문 실패 — API 오류 (ticker={ticker}, qty={qty:.8f})")
    if isinstance(result, dict) and "error" in result:
        raise RuntimeError(f"매도 주문 거부 — {result['error']} (ticker={ticker}, qty={qty:.8f})")
    return result
