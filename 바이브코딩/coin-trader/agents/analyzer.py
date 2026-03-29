import pyupbit
import pandas as pd
import numpy as np
from utils.upbit_client import get_krw_tickers, get_current_price


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)


def _macd_signal(series: pd.Series) -> str:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    diff = macd.iloc[-1] - signal.iloc[-1]
    prev_diff = macd.iloc[-2] - signal.iloc[-2]
    if prev_diff < 0 and diff > 0:
        return "골든크로스(강한매수)"
    elif prev_diff > 0 and diff < 0:
        return "데드크로스(강한매도)"
    elif diff > 0:
        return "상승"
    else:
        return "하락"


def _adx(df: pd.DataFrame, period: int = 14) -> float:
    """ADX (Average Directional Index) — 추세 강도 측정. 20 이상이면 추세 존재"""
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).fillna(0)
    return round(float(dx.ewm(span=period, adjust=False).mean().iloc[-1]), 1)


def _bb_position(series: pd.Series, period: int = 20) -> str:
    ma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    price = series.iloc[-1]
    u, m, l = float(upper.iloc[-1]), float(ma.iloc[-1]), float(lower.iloc[-1])
    if price >= u:
        return "상단(과매수)"
    elif price <= l:
        return "하단(과매도)"
    else:
        mid = (u + l) / 2
        return "중상단" if price > mid else "중하단"


def get_top_tickers(n: int = 20) -> list:
    """24h 거래대금 기준 상위 n개 KRW 티커 반환"""
    tickers = get_krw_tickers()
    try:
        prices = pyupbit.get_current_price(tickers)
        if not isinstance(prices, dict):
            return tickers[:n]
        # 거래대금 = 현재가 × 거래량 (pyupbit은 거래대금을 직접 제공하지 않으므로
        # acc_trade_price_24h 포함된 ticker 정보 활용)
        import requests
        url = "https://api.upbit.com/v1/ticker"
        markets = ",".join(tickers[:200])  # 최대 200개
        r = requests.get(url, params={"markets": markets}, timeout=10)
        data = r.json()
        sorted_data = sorted(data, key=lambda x: x.get("acc_trade_price_24h", 0), reverse=True)
        return [d["market"] for d in sorted_data[:n]]
    except Exception as e:
        print(f"  ⚠️  상위 종목 조회 실패, 기본 목록 사용: {e}")
        return tickers[:n]


def analyze_ticker(ticker: str) -> dict | None:
    """한 종목의 4시간봉 기술적 지표 계산. 실패 시 None 반환"""
    try:
        df = pyupbit.get_ohlcv(ticker, interval="minute240", count=100)
        if df is None or len(df) < 30:
            return None

        close = df["close"]
        volume = df["volume"]

        rsi = _rsi(close)
        macd_sig = _macd_signal(close)
        bb_pos = _bb_position(close)
        adx = _adx(df)

        # 24h 거래량 변화율 (마지막 6개 4h봉 vs 그 이전 6개)
        recent_vol = volume.iloc[-6:].sum()
        prev_vol = volume.iloc[-12:-6].sum()
        vol_chg = round((recent_vol / prev_vol - 1) * 100, 1) if prev_vol > 0 else 0.0

        price = get_current_price(ticker)

        return {
            "ticker": ticker,
            "price": price,
            "rsi": rsi,
            "macd": macd_sig,
            "bb": bb_pos,
            "vol_change_pct": vol_chg,
            "adx": adx,
        }
    except Exception as e:
        print(f"  ⚠️  [{ticker}] 분석 실패: {e}")
        return None


def run(top_n: int = 20) -> list:
    """상위 종목 분석 결과 리스트 반환"""
    print("📊 분석 에이전트 실행 중...")
    tickers = get_top_tickers(top_n)
    print(f"  대상 종목: {len(tickers)}개")

    results = []
    for ticker in tickers:
        info = analyze_ticker(ticker)
        if info:
            results.append(info)

    print(f"  ✅ {len(results)}개 종목 분석 완료")
    return results
