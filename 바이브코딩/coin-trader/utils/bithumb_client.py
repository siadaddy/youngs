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
    """주문 가능 KRW 잔고 반환 (total_krw - in_use_krw)"""
    b = get_bithumb()
    if b is None:
        return float(os.getenv("MAX_INVEST_KRW", "80000")) * 2  # dry run 가상 잔고
    # get_balance(coin) → (보유코인, 사용중코인, total_krw, in_use_krw)
    result = b.get_balance("BTC")
    if isinstance(result, tuple) and len(result) >= 4:
        total_krw  = float(result[2])
        in_use_krw = float(result[3])
        return total_krw - in_use_krw  # 실제 주문 가능 금액
    if isinstance(result, tuple) and len(result) >= 3:
        return float(result[2])
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
    """시장가 매수. DRY_RUN이면 시뮬레이션."""
    coin = ticker.replace("KRW-", "")
    b = get_bithumb()

    if b is None:
        price = get_current_price(coin)
        qty = amount_krw / price if price else 0
        print(f"  [DRY RUN] 매수 시뮬레이션: {coin} {qty:.6f}개 @ {price:,.0f}원 ({amount_krw:,.0f}원)")
        return {"ticker": coin, "price": price, "qty": qty, "dry_run": True}

    # 실제 주문 가능 잔고 조회
    raw_bal = b.api.balance(currency="BTC")
    avail_krw = float(raw_bal["data"]["available_krw"])

    # 잔고의 75%만 투자 — 수수료(0.25%) + 호가 슬리피지 여유 확보
    invest = avail_krw * 0.75
    price = get_current_price(coin)
    if not price:
        raise RuntimeError(f"현재가 조회 실패 (ticker={coin})")
    qty = invest / price
    print(f"  💰 잔고: {avail_krw:,.0f}원 | 주문: {qty:.4f}개 @ {price:,.0f}원 ({invest:,.0f}원)")


    result = b.buy_market_order(coin, qty)
    print(f"  🔎 Bithumb 응답: {result}")

    if result is None:
        raise RuntimeError(f"매수 API 오류 (ticker={coin})")
    if isinstance(result, tuple):
        return result  # 성공: ("bid", coin, order_id, "KRW")
    if isinstance(result, dict):
        status = result.get("status", "")
        if status not in (None, "0000"):
            raise RuntimeError(f"매수 거부 [{status}] {result.get('message','')} (ticker={coin}, {invest:,.0f}원)")
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
