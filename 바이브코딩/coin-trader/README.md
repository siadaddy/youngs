# 🤖 AI 코인 자동매매 시스템

> 소액으로 AI가 알아서 종목 선정, 매수/매도를 반복하는 완전 자동 트레이딩 시스템

**실행 환경**: MacBook (launchd) — 4시간마다 자동 실행

---

## 📋 시스템 개요

업비트 KRW 전체 마켓에서 거래량 상위 20개 종목을 분석하고,
Groq AI(Llama 3.3 70B)가 기술적 지표를 바탕으로 BUY / SELL / HOLD를 판단합니다.

---

## 🕐 자동화 흐름

```
00:00 / 04:00 / 08:00 / 12:00 / 16:00 / 20:00 (하루 6회)
│
├─ Step 0: 공인 IP 변경 감지 → IP 바뀌면 ntfy 긴급 알림
├─ Step 1: state.json 로드 → 현재 보유 종목 확인
├─ Step 2: 손절 체크 (보유 중 && 매수가 대비 -5% 이하 → 즉시 매도)
├─ Step 3: 업비트 KRW 마켓 거래량 상위 20개 종목 선별
├─ Step 4: 각 종목 4시간봉 OHLCV → RSI / MACD / 볼린저밴드 계산
├─ Step 5: Groq AI 판단 → BUY(종목명) / SELL / HOLD + 한국어 이유
├─ Step 6: 주문 실행 (업비트 시장가)
├─ Step 7: state.json 업데이트
├─ Step 8: ntfy 결과 알림
└─ Step 9: docs/trades.json 업데이트 → GitHub Pages push

🛡 가격 감시 (price_guard.py) — 상시 실행 (30초 간격)
├─ 보유 종목 현재가 실시간 조회
├─ 손절 발동: 매수가 대비 -7% 이하 → 즉시 시장가 매도 + ntfy 긴급 알림
└─ 익절 발동: 매수가 대비 +15% 이상 → 즉시 시장가 매도 + ntfy 알림
```

---

## 🗂 파일 구조

```
coin-trader/
├── main.py                 ← 오케스트레이터 (4시간마다)
├── price_guard.py          ← 실시간 가격 감시 (30초 간격, 손절/익절)
├── run_trader.sh           ← launchd 실행 스크립트
├── state.json              ← 보유 종목·매수가·수량 (재시작 시 복원)
├── ip.txt                  ← 마지막 확인 공인 IP (변경 감지용)
├── trader.log              ← 실행 로그
├── agents/
│   ├── analyzer.py         ← 거래량 상위 20개 + 기술적 지표 계산
│   ├── ai_advisor.py       ← Groq AI 판단 (key1→key2 폴백, 외국어 필터)
│   └── executor.py         ← 업비트 시장가 주문 실행
└── utils/
    └── upbit_client.py     ← pyupbit 래퍼 (잔고·현재가·매수·매도)
```

---

## 🔧 .env 설정

```
UPBIT_ACCESS_KEY=...        # 업비트 Open API 키 (주문 권한 필수)
UPBIT_SECRET_KEY=...
GROQ_API_KEY=...            # key1 소진 시 key2 자동 전환
GROQ_API_KEY_2=...
MAX_INVEST_KRW=5000         # 최대 투자금액 (원)
STOP_LOSS_PCT=7.0           # 자동 손절 기준 (%, price_guard 기본값)
TAKE_PROFIT_PCT=15.0        # 자동 익절 기준 (%, price_guard 기본값)
DRY_RUN=false               # true=시뮬레이션, false=실제 주문
NTFY_TOPIC=siadad-aicrew
```

---

## 🧠 기술적 지표

| 지표 | 설정 | 매수 신호 | 매도 신호 |
|------|------|----------|----------|
| RSI | 14 | 30 이하 (과매도) | 70 이상 (과매수) |
| MACD | 12/26/9 | 골든크로스 | 데드크로스 |
| 볼린저밴드 | 20/2 | 하단 근접 | 상단 근접 |

분석 기준: **4시간봉** (노이즈 최소화, 추세 반영)

---

## 🛡 안전장치

| 기능 | 내용 |
|------|------|
| 손절 | 매수가 대비 -7% 자동 매도 (price_guard 실시간 감시) |
| 익절 | 매수가 대비 +15% 자동 매도 (price_guard 실시간 감시) |
| IP 변경 감지 | 공인 IP 변경 시 ntfy 긴급 알림 (업비트 API 재등록 안내) |
| 주문 실패 감지 | buy/sell_market_order None 반환 시 예외 발생 (silent 실패 방지) |
| Groq 폴백 | key1 소진 시 key2 자동 전환, 429 rate limit 대기 처리 |
| 외국어 필터 | AI 응답에서 한자·일본어·아랍어·키릴 자동 제거 |
| DRY_RUN | 실제 주문 없이 전체 흐름 시뮬레이션 |

---

## 📊 GitHub Pages 대시보드

**라이브**: `https://siadaddy.github.io/youngs/` → 코인 트레이더 탭

- 매매 통계 (총 거래 / 승 / 패 / 손익)
- 현재 보유 종목 실시간 표시
- 최근 50건 매매 이력 + AI 판단 이유

---

## 📱 ntfy 알림

| 상황 | 알림 |
|------|------|
| 매수 완료 | 🟢 종목·단가·AI 이유 |
| 매도 완료 | 🔴 종목·이유 |
| 손절 매도 | 🔴 긴급 — 손절 기준 도달 |
| HOLD | ⏸ 낮은 우선순위 |
| IP 변경 | 🔴 긴급 — 업비트 재등록 필요 |
| 오류 | ❌ 단계별 실패 알림 |

---

## 🚀 수동 실행

```bash
cd /Users/youngchulyu/바이브코딩/coin-trader

# 전체 실행
python3 main.py

# 잔고 확인
python3 -c "from utils.upbit_client import get_krw_balance, get_coin_balance; print(get_krw_balance())"

# 로그 확인
tail -f trader.log
```

---

## ⚙️ launchd 관리

```bash
# 상태 확인
launchctl list | grep cointrader

# 재시작 (설정 변경 후)
launchctl unload ~/Library/LaunchAgents/com.siadad.cointrader.plist
launchctl load ~/Library/LaunchAgents/com.siadad.cointrader.plist

# 수동 즉시 실행
launchctl start com.siadad.cointrader
```

> **맥북 재시작 후**: 로그인하면 launchd가 자동으로 plist를 다시 로드합니다. 별도 작업 불필요.

---

## 🛠 설치

```bash
pip install pyupbit pandas numpy python-dotenv requests
```

---

## 📝 업데이트 로그

### 2026-03-31
- **price_guard.py 추가**: 30초 간격 실시간 가격 감시 (별도 launchd 데몬)
  - 손절 기준 -5% → **-7%** 조정
  - 익절 기준 **+15%** 추가
  - `com.siadad.coinreport` launchd 서비스로 상시 실행

### 2026-03-28
- 시스템 최초 구축
- IP 변경 감지 + ntfy 긴급 알림 추가
- buy/sell_market_order None 반환 시 예외 처리 (silent 실패 방지)
- GitHub Pages 코인 트레이더 대시보드 탭 추가
- docs/trades.json 자동 업데이트 + git push

---

*최종 업데이트: 2026-03-31 | Powered by Groq + pyupbit + GitHub Pages*
