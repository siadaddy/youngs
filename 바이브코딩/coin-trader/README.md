# 🤖 AI 코인 자동매매 시스템

> 소액으로 AI가 알아서 종목 선정, 매수/매도를 반복하는 완전 자동 트레이딩 시스템

**실행 환경**: MacBook (launchd) — 매 시간 자동 실행

---

## 📋 시스템 개요

업비트 KRW 전체 마켓에서 거래량 상위 20개 종목을 분석하고,
Groq AI(Llama 3.3 70B)가 기술적 지표를 바탕으로 BUY / SELL / HOLD를 판단합니다.

---

## 🕐 자동화 흐름

```
매 시간 :05분 (하루 24회)
│
├─ Step 0: 공인 IP 변경 감지 → IP 바뀌면 ntfy 긴급 알림
├─ Step 1: state.json 로드 → 현재 보유 종목 확인
├─ Step 2: 손절/익절 체크 (price_guard 실시간 감시)
├─ Step 3: 업비트 KRW 마켓 거래량 상위 20개 종목 선별
├─ Step 4: 각 종목 1시간봉 OHLCV → RSI / MACD / 볼린저밴드 / ADX / 변동성돌파 계산
├─ Step 5: Groq AI 판단 → BUY(종목명) / SELL / HOLD + 한국어 이유
├─ Step 6: 주문 실행 (업비트 시장가, 매도 최소금액 5,000원 체크)
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
├── main.py                 ← 오케스트레이터 (매 시간)
├── price_guard.py          ← 실시간 가격 감시 (30초 간격, 손절/익절)
├── run_trader.sh           ← launchd 실행 스크립트
├── state.json              ← 보유 종목·매수가·수량 (재시작 시 복원)
├── ip.txt                  ← 마지막 확인 공인 IP (변경 감지용)
├── trader.log              ← 실행 로그
├── agents/
│   ├── analyzer.py         ← 거래량 상위 20개 + 기술적 지표 계산
│   ├── ai_advisor.py       ← Groq AI 판단 (key1→key2 폴백, 외국어 필터)
│   └── executor.py         ← 업비트 시장가 주문 실행 + 최소금액 체크
└── utils/
    └── upbit_client.py     ← pyupbit 래퍼 (잔고·현재가·매수·매도·에러 감지)
```

---

## 🔧 .env 설정

```
UPBIT_ACCESS_KEY=...        # 업비트 Open API 키 (주문 권한 필수)
UPBIT_SECRET_KEY=...
GROQ_API_KEY=...            # key1 소진 시 key2 자동 전환
GROQ_API_KEY_2=...
MAX_INVEST_KRW=10000        # 최대 투자금액 (원) — 소액 손실 후 매도 불가 방지
STOP_LOSS_PCT=7.0           # 자동 손절 기준 (%, price_guard 기본값)
TAKE_PROFIT_PCT=15.0        # 자동 익절 기준 (%, price_guard 기본값)
DRY_RUN=false               # true=시뮬레이션, false=실제 주문
NTFY_TOPIC=siadad-aicrew
```

---

## 🧠 기술적 지표 & 스코어링

| 지표 | 설정 | 매수 점수 | 매도 점수 |
|------|------|----------|----------|
| RSI | 14 | <35: +2 / <45: +1 | >65: -1 / >75: -2 |
| MACD | 12/26/9 | 골든크로스: +2 / 상승: +1 | 데드크로스: -2 / 하락: -1 |
| 볼린저밴드 | 20/2 | 하단: +2 / 중하단: +1 | 상단: -2 / 중상단: -1 |
| ADX | 14 | ≥15: 추세O (매수 허용) | <10: 횡보 (매수 금지) |
| **변동성 돌파(VB)** | K=0.5 | **+2 보너스** (최우선 매수 신호) | — |

분석 기준: **1시간봉** (매 시간 실행에 최적화)

**변동성 돌파 공식**: `오늘 시가 + (전일 고가 - 전일 저가) × 0.5`
현재가가 이 목표가를 돌파하면 VB✅ 신호 발생

---

## 📋 매매 판단 규칙

1. **VB 매수 (최우선)**: 미보유 시 VB✅ + 점수 +1 이상 → BUY
2. **강한 매수**: 점수 +3 이상 + ADX 15 이상 → BUY
3. **중간 매수**: 점수 +2 이상 + ADX 15 이상 + 거래량 +20% 이상 → BUY
4. **매도**: 보유 종목 점수 -2 이하 또는 RSI 70+ + MACD 하락/데드크로스 → SELL
5. **기회 교체**: 보유 수익률 +5% 미만 + 점수 0 이하일 때, 다른 종목 VB✅ 또는 점수 +3 이상 → 즉시 교체
6. **매도 보류**: qty × 현재가 < 5,000원이면 가격 회복까지 대기

---

## 🛡 안전장치

| 기능 | 내용 |
|------|------|
| 손절 | 매수가 대비 -7% 자동 매도 (price_guard 실시간 감시) |
| 익절 | 매수가 대비 +15% 자동 매도 (price_guard 실시간 감시) |
| 매도 최소금액 체크 | qty × 현재가 < 5,000원이면 매도 보류 (업비트 under_min_total_market_ask 방지) |
| API 에러 응답 감지 | buy/sell 결과에 error 키 포함 시 RuntimeError 발생 (silent 실패 방지) |
| IP 변경 감지 | 공인 IP 변경 시 ntfy 긴급 알림 (업비트 API 재등록 안내) |
| Groq 폴백 | key1 소진 시 key2 자동 전환, 429 rate limit 대기 처리 |
| 외국어 필터 | AI 응답에서 한자·일본어·아랍어·키릴 자동 제거 |
| DRY_RUN | 실제 주문 없이 전체 흐름 시뮬레이션 |

---

## 📊 GitHub Pages 대시보드

**라이브**: `https://siadaddy.github.io/youngs/` → 코인 트레이더 탭

- 매매 통계 (총 거래 / 승 / 패 / 손익)
- 현재 보유 종목 실시간 표시 (30초 갱신)
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

# 실제 잔고 확인
python3 -c "
from utils.upbit_client import get_upbit, get_krw_balance, get_current_price
upbit = get_upbit()
for b in upbit.get_balances():
    if float(b['balance']) > 0.000001:
        print(b['currency'], b['balance'], b['avg_buy_price'])
"

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
```

> **맥북 재시작 후**: 로그인하면 launchd가 자동으로 plist를 다시 로드합니다.

---

## 🛠 설치

```bash
pip install pyupbit pandas numpy python-dotenv requests
```

---

## 📝 업데이트 로그

### 2026-04-02
- **변동성 돌파(VB) 전략 추가**: 한국 자동매매 커뮤니티 검증 1위 전략
  - 일봉 기준 `오늘 시가 + (전일 고저차 × 0.5)` 목표가 계산
  - VB✅ 종목은 점수 +2 보너스 + 최우선 매수 신호로 처리
- **1시간봉 전환**: minute240 → minute60, 거래량 윈도우 6→24봉
- **매 시간 실행**: launchd 6회/일 → 24회/일 (매 시간 :05분)
- **매매 조건 완화**: 매수 점수 +4→+3, ADX 20→15, 기회 교체 임계치 완화
- **매도 최소금액 체크**: qty × 현재가 < 5,000원이면 보류 (under_min_total_market_ask 방지)
- **API 에러 응답 감지**: error dict 반환 시 RuntimeError — silent SELL 실패 버그 수정
- **MAX_INVEST_KRW 10,000으로 상향**: 5,000원 투자 시 소폭 하락만으로 매도 불가 문제 해결

### 2026-03-31
- **price_guard.py 추가**: 30초 간격 실시간 가격 감시 (별도 launchd 데몬)
  - 손절 기준 -5% → **-7%** 조정
  - 익절 기준 **+15%** 추가

### 2026-03-28
- 시스템 최초 구축
- IP 변경 감지 + ntfy 긴급 알림 추가
- GitHub Pages 코인 트레이더 대시보드 탭 추가

---

*최종 업데이트: 2026-04-02 | Powered by Groq + pyupbit + Pollinations.ai + GitHub Pages*
