"""
📚 학습 블랙리스트 시스템
━━━━━━━━━━━━━━━━━━━━━━━━
손절 횟수를 누적 학습하여 반복 손절 종목 자동 차단.
blacklist.json에 영구 저장 — 재시작해도 기억 유지.

손절 횟수별 차단 기간:
  1회: 차단 없음 (6h 쿨다운만)
  2회: 3일 차단
  3회: 7일 차단
  4회: 14일 차단
  5회 이상: 30일 차단
"""

import os, json
from datetime import datetime, timedelta

BLACKLIST_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "blacklist.json")

# 손절 횟수 → 블랙리스트 일수
BLACKLIST_SCHEDULE = {1: 0, 2: 3, 3: 7, 4: 14}
DEFAULT_BAN_DAYS = 30  # 5회 이상


def load_blacklist() -> dict:
    if not os.path.exists(BLACKLIST_FILE):
        return {}
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_blacklist(data: dict):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register_stop_loss(ticker: str) -> dict:
    """
    손절 발생 시 호출.
    - 손절 횟수 누적
    - 2회 이상이면 블랙리스트 등록 (기간은 횟수에 비례)
    반환: 해당 종목의 블랙리스트 정보
    """
    data = load_blacklist()
    coin = ticker.replace("KRW-", "").upper()

    if coin not in data:
        data[coin] = {"stop_loss_count": 0, "last_stop_loss": None, "blacklisted_until": None, "history": []}

    entry = data[coin]
    entry["stop_loss_count"] += 1
    entry["last_stop_loss"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry["history"].append(entry["last_stop_loss"])
    entry["history"] = entry["history"][-10:]  # 최근 10건만 보관

    count = entry["stop_loss_count"]
    ban_days = BLACKLIST_SCHEDULE.get(count, DEFAULT_BAN_DAYS if count > max(BLACKLIST_SCHEDULE) else 0)

    if ban_days > 0:
        until = (datetime.now() + timedelta(days=ban_days)).strftime("%Y-%m-%d %H:%M")
        entry["blacklisted_until"] = until
        print(f"  🚫 블랙리스트 등록: {coin} | 손절 {count}회 → {ban_days}일 차단 (해제: {until})")
    else:
        print(f"  📋 손절 기록: {coin} | {count}회째 (2회부터 차단 시작)")

    data[coin] = entry
    save_blacklist(data)
    return entry


def get_blacklisted_tickers() -> list:
    """현재 차단 중인 종목 목록 반환"""
    data = load_blacklist()
    now = datetime.now()
    active = []
    for coin, info in data.items():
        until_str = info.get("blacklisted_until")
        if not until_str:
            continue
        try:
            if now < datetime.strptime(until_str, "%Y-%m-%d %H:%M"):
                active.append(coin)
        except Exception:
            pass
    return active


def is_blacklisted(ticker: str) -> bool:
    """특정 종목이 현재 차단 중인지 확인"""
    coin = ticker.replace("KRW-", "").upper()
    return coin in get_blacklisted_tickers()


def get_summary() -> list[str]:
    """블랙리스트 현황 출력용 요약"""
    data = load_blacklist()
    now = datetime.now()
    lines = []
    for coin, info in sorted(data.items()):
        count = info.get("stop_loss_count", 0)
        until_str = info.get("blacklisted_until")
        if until_str:
            try:
                until = datetime.strptime(until_str, "%Y-%m-%d %H:%M")
                status = f"🚫 차단 중 (해제: {until_str})" if now < until else "✅ 차단 만료"
            except Exception:
                status = "?"
        else:
            status = f"⚠️ 경고 {count}회 (차단 전)"
        lines.append(f"  {coin}: 손절 {count}회 | {status}")
    return lines


def add_successful_trade(ticker: str) -> dict:
    """
    수익 거래 완료 시 호출. 복구 카운트 누적.
    3회 수익 달성 시 손절 카운트 1 감소 (차단 기간 자체는 유지 — 리스크 보호).
    """
    data = load_blacklist()
    coin = ticker.replace("KRW-", "").upper()

    if coin not in data:
        return {}  # 손절 이력 없는 종목은 기록 불필요

    entry = data[coin]
    entry["recovery_trades"] = entry.get("recovery_trades", 0) + 1

    if entry["recovery_trades"] >= 3:
        old_count = entry["stop_loss_count"]
        if old_count > 1:
            entry["stop_loss_count"] = max(1, old_count - 1)
            print(f"  ✅ {coin}: 3회 수익 달성 → 손절 카운트 {old_count} → {entry['stop_loss_count']} 감소 (학습 개선)")
        entry["recovery_trades"] = 0
        print(f"  🔄 {coin}: 복구 카운터 리셋")

    data[coin] = entry
    save_blacklist(data)
    return entry


def init_from_history(trades_path: str):
    """
    trades.json 거래 기록에서 손절 이력을 읽어 블랙리스트 초기화.
    봇 최초 실행 또는 블랙리스트.json 없을 때 호출.
    이미 등록된 종목은 덮어쓰지 않음.
    """
    if not os.path.exists(trades_path):
        return

    try:
        with open(trades_path, "r", encoding="utf-8") as f:
            trades = json.load(f)
    except Exception:
        return

    history = trades.get("history", [])
    existing = load_blacklist()

    # 실시간 손절(price_guard)과 AI 손절 모두 카운트
    stop_losses: dict[str, list[str]] = {}
    for entry in history:
        if entry.get("action") != "SELL":
            continue
        reason = entry.get("reason", "")
        pnl = entry.get("pnl_pct")
        # 손절 판별: reason에 "손절" 포함 또는 pnl < -2.0% (STOP_LOSS 기준 근방)
        if "손절" in reason or (pnl is not None and pnl <= -2.0):
            coin = entry.get("ticker", "").replace("KRW-", "").upper()
            if coin:
                stop_losses.setdefault(coin, [])
                stop_losses[coin].append(entry.get("time", ""))

    # 블랙리스트에 없는 종목만 등록 (기존 데이터 보호)
    data = existing.copy()
    new_count = 0
    for coin, times in stop_losses.items():
        if coin in data:
            continue  # 이미 있으면 스킵
        count = len(times)
        ban_days = BLACKLIST_SCHEDULE.get(count, DEFAULT_BAN_DAYS if count > max(BLACKLIST_SCHEDULE) else 0)
        until = None
        if ban_days > 0:
            # 마지막 손절 기준으로 차단 기간 계산
            last = max(times)
            try:
                last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M")
                until_dt = last_dt + timedelta(days=ban_days)
                # 이미 만료됐으면 기록만 남기고 차단 없음
                until = until_dt.strftime("%Y-%m-%d %H:%M") if until_dt > datetime.now() else None
            except Exception:
                pass
        data[coin] = {
            "stop_loss_count": count,
            "last_stop_loss": max(times),
            "blacklisted_until": until,
            "history": sorted(times)[-10:],
        }
        new_count += 1

    if new_count > 0:
        save_blacklist(data)
        print(f"  📚 블랙리스트 초기화: 거래 기록에서 {new_count}개 종목 등록 완료")
