import pybithumb
import pandas as pd
import numpy as np
from utils.bithumb_client import get_krw_tickers, get_current_price


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = float(rsi.iloc[-1])
    return round(val if np.isfinite(val) else 50.0, 1)  # NaN/Inf → 중립값 50


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
    val = float(dx.ewm(span=period, adjust=False).mean().iloc[-1])
    return round(val if np.isfinite(val) else 0.0, 1)  # NaN/Inf → 0 (추세 없음)


def _vol_breakout_target(ticker: str, k: float = 0.5) -> float | None:
    """변동성 돌파 목표가: 오늘 시가 + (전일 고저차 × K). 실패 시 None"""
    try:
        coin = ticker.replace("KRW-", "")
        df = pybithumb.get_ohlcv(coin, interval="day")
        if df is None or len(df) < 2:
            return None
        today_open = float(df["open"].iloc[-1])
        prev_high  = float(df["high"].iloc[-2])
        prev_low   = float(df["low"].iloc[-2])
        return today_open + (prev_high - prev_low) * k
    except Exception:
        return None


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


def get_top_tickers(n: int = 15) -> list:
    """24h 거래대금 기준 상위 n개 빗썸 티커 반환 (BTC 형식)"""
    tickers = get_krw_tickers() or []
    try:
        import requests
        # 빗썸 공개 API — 전체 종목 시세 (거래대금 포함)
        r = requests.get("https://api.bithumb.com/public/ticker/ALL_KRW", timeout=10)
        data = r.json().get("data", {})
        # acc_trade_value: 24h 거래대금
        ranked = sorted(
            [(coin, float(info.get("acc_trade_value", 0)))
             for coin, info in data.items() if coin != "date" and coin in tickers],
            key=lambda x: x[1], reverse=True
        )
        return [coin for coin, _ in ranked[:n]]
    except Exception as e:
        print(f"  ⚠️  상위 종목 조회 실패, 기본 목록 사용: {e}")
        return tickers[:n]


def analyze_ticker(ticker: str) -> dict | None:
    """한 종목의 15분봉 기술적 지표 + 변동성 돌파 신호 계산. 실패 시 None 반환"""
    try:
        coin = ticker.replace("KRW-", "")
        df = pybithumb.get_ohlcv(coin, interval="minute30")
        if df is None or len(df) < 30:
            return None

        close = df["close"]
        volume = df["volume"]

        rsi = _rsi(close, period=14)       # 30분봉 — 14봉(7시간) 표준 RSI
        macd_sig = _macd_signal(close)
        bb_pos = _bb_position(close, period=20)
        adx = _adx(df, period=14)          # 30분봉 — 14봉 표준 ADX

        # 4h 거래량 변화율 (최근 8개 30분봉 vs 그 이전 8개)
        recent_vol = volume.iloc[-8:].sum()
        prev_vol = volume.iloc[-16:-8].sum()
        vol_chg = round((recent_vol / prev_vol - 1) * 100, 1) if prev_vol > 0 else 0.0

        price = get_current_price(coin)

        # 변동성 돌파 신호 (일봉 기준, K=0.5)
        vb_target = _vol_breakout_target(coin)
        vb = bool(vb_target and price > vb_target)

        return {
            "ticker": coin,
            "price": price,
            "rsi": rsi,
            "macd": macd_sig,
            "bb": bb_pos,
            "vol_change_pct": vol_chg,
            "adx": adx,
            "vb": vb,
        }
    except Exception as e:
        print(f"  ⚠️  [{coin}] 분석 실패: {e}")
        return None


def run(top_n: int = 15) -> list:
    """상위 종목 분석 결과 리스트 반환 — 병렬 처리(max_workers=5)로 속도 개선"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    print("📊 분석 에이전트 실행 중...")
    tickers = get_top_tickers(top_n)
    print(f"  대상 종목: {len(tickers)}개 (병렬 분석)")

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ticker = {executor.submit(analyze_ticker, t): t for t in tickers}
        try:
            for future in as_completed(future_to_ticker, timeout=120):
                try:
                    info = future.result(timeout=30)
                    if info:
                        results.append(info)
                except Exception as e:
                    ticker = future_to_ticker[future]
                    print(f"  ⚠️  [{ticker}] 분석 오류: {e}")
        except Exception:
            # 120초 전체 타임아웃 — 지금까지 완료된 결과만 사용
            print("  ⚠️  병렬 분석 120초 초과 — 완료된 종목만 사용")

    print(f"  ✅ {len(results)}개 종목 분석 완료")
    return results
