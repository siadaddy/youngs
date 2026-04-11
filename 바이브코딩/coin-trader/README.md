# 🤖 AI 코인 자동매매 시스템

> 빗썸 KRW 마켓에서 AI가 종목 선정·매수·매도를 완전 자동화하는 트레이딩 시스템

**실행 환경**: MacBook (launchd) — 5분마다 자동 실행 (288회/일)

---

## 📋 시스템 개요

빗썸 KRW 전체 마켓에서 거래대금 상위 20개 종목을 분석하고,
Groq AI(Llama 3.3 70B)가 기술적 지표를 바탕으로 BUY / SELL / HOLD를 판단합니다.

---

## 🕐 자동화 흐름

```
매 시 :00 / :05 / :10 / ... / :55 (하루 288회)
│
├─ Step 0: Daily Drawdown 체크 → 일일 손실 한도 도달 시 당일 봇 정지
├─ Step 1: 공인 IP 변경 감지 → 변경 시 ntfy 긴급 알림
├─ Step 2: state.json 로드 → 현재 보유 종목 확인
├─ Step 3: 손절/익절 체크 → 발동 시 즉시 매도 후 BUY 재탐색
├─ Step 4: 빗썸 KRW 마켓 거래대금 상위 20개 종목 선별
├─ Step 5: 각 종목 30분봉 OHLCV → RSI / MACD / 볼린저밴드 / ADX / 변동성돌파 계산
│           (ThreadPoolExecutor max_workers=5 병렬 처리)
├─ Step 6: Groq AI 판단 → BUY(종목명) / SELL / HOLD + 한국어 이유
├─ Step 7: 주문 실행 (빗썸 시장가, 최소금액 5,000원 체크)
│   └─ SELL 직후 → holding=None으로 즉시 BUY 재판단 → 신호 있으면 바로 매수
├─ Step 8: state.json 업데이트
├─ Step 9: ntfy 결과 알림
└─ Step 10: docs/trades.json 업데이트 → GitHub Pages push
```

---

## 🗂 파일 구조

```
coin-trader/
├── main.py                 ← 오케스트레이터 (5분 간격)
├── price_guard.py          ← 실시간 가격 감시 (30초 간격, 손절/익절 백업)
├── run_trader.sh           ← launchd 실행 스크립트
├── state.json              ← 보유 종목·매수가·수량 (재시작 시 복원)
├── drawdown.json           ← 일일 손실 누적 추적 (자정 자동 초기화)
├── ip.txt                  ← 마지막 확인 공인 IP (변경 감지용)
├── trader.log              ← 실행 로그
├── agents/
│   ├── analyzer.py         ← 거래량 상위 20개 + 30분봉 기술적 지표 계산 (병렬)
│   ├── ai_advisor.py       ← Groq AI 판단 (key1→key2 폴백, 외국어 필터)
│   └── executor.py         ← 빗썸 시장가 주문 실행 + 최소금액 체크
└── utils/
    ├── bithumb_client.py   ← pybithumb 래퍼 (잔고·현재가·매수·매도)
    └── upbit_client.py     ← 레거시 (미사용)
```

---

## 🔧 .env 설정

```
BITHUMB_ACCESS_KEY=...      # 빗썸 API 1.0 키 (주문 권한 필수)
BITHUMB_SECRET_KEY=...
BITHUMB_ACCESS_KEY_V2=...   # API 2.0 (IP 관리 가능 — 추후 전환용, 현재 미사용)
BITHUMB_SECRET_KEY_V2=...
GROQ_API_KEY=...            # key1 소진 시 key2 자동 전환
GROQ_API_KEY_2=...
MAX_INVEST_KRW=100000       # 최대 투자금액 (원)
STOP_LOSS_PCT=4.0           # 자동 손절 기준 (%)
TAKE_PROFIT_PCT=6.0         # 자동 익절 기준 (%)
DAILY_LOSS_LIMIT_KRW=-15000 # 일일 손실 한도 (원, 초과 시 당일 봇 정지)
DRY_RUN=false               # true=시뮬레이션, false=실제 주문
NTFY_TOPIC=siadad-aicrew
```

---

## 🧠 기술적 지표 & 스코어링

| 지표 | 설정 | 매수 점수 | 매도 점수 |
|------|------|----------|----------|
| RSI | **14봉** (30분봉 기준 표준) | <35: +2 / <45: +1 | >65: -1 / >75: -2 |
| MACD | 12/26/9 | 골든크로스: +2 / 상승: +1 | 데드크로스: -2 / 하락: -1 |
| 볼린저밴드 | 20/2 | 하단: +2 / 중하단: +1 | 상단: -2 / 중상단: -1 |
| ADX | **14봉** | ≥15: 추세O (매수 허용) | <10: 횡보 (매수 금지) |
| **변동성 돌파(VB)** | K=0.5 (일봉) | **+2 보너스** (최우선 매수 신호) | — |

분석 기준: **30분봉** (minute30)

**변동성 돌파 공식**: `오늘 시가 + (전일 고가 - 전일 저가) × 0.5`
현재가가 이 목표가를 돌파하면 VB✅ 신호 발생

---

## 📋 매매 판단 규칙

1. **VB 매수 (최우선)**: 미보유 시 VB✅ + 점수 +1 이상 → BUY
2. **강한 매수**: 점수 +3 이상 + ADX 15 이상 → BUY
3. **중간 매수**: 점수 +2 이상 + ADX 15 이상 + 거래량 +20% 이상 → BUY
4. **매도**: 보유 종목 점수 -2 이하 또는 RSI 70+ + MACD 하락/데드크로스 → SELL
5. **기회 교체**: 보유 수익률 +5% 미만 + 점수 0 이하 + 다른 종목 VB✅/점수+3 → 즉시 SELL 후 BUY
6. **SELL 직후 재탐색**: 매도 완료 즉시 holding=None으로 AI 재판단 → BUY 신호 있으면 같은 사이클 내 매수
7. **수익 보호**: 보유 수익률 +5% 이상이면 교체 금지
8. **횡보 금지**: ADX <10 + VB❌ 종목은 BUY 금지

---

## 🛡 안전장치

| 기능 | 내용 |
|------|------|
| 손절 | 매수가 대비 -4% 자동 매도 |
| 익절 | 매수가 대비 +6% 자동 매도 |
| Daily Drawdown | 일일 누적 손실 -15,000원 초과 시 당일 봇 정지 (자정 초기화) |
| 매도 최소금액 체크 | qty × 현재가 < 5,000원이면 매도 보류 |
| IP 변경 감지 | 공인 IP 변경 시 ntfy 긴급 알림 (빗썸 API 재등록 안내) |
| Groq 폴백 | key1 소진 시 key2 자동 전환, 429 rate limit 대기 처리 |
| 외국어 필터 | AI 응답에서 한자·일본어·아랍어·키릴 자동 제거 |
| DRY_RUN | 실제 주문 없이 전체 흐름 시뮬레이션 |
| 전체 타임아웃 | 10분 초과 시 강제 종료 (BaseException 하드킬) |

---

## 💻 맥북 뚜껑 닫힘 설정 (필수)

LaunchAgent는 시스템이 절전 상태면 실행되지 않습니다.
전원 연결 상태에서 절전 비활성화 필요:

```bash
# AC 전원 연결 시 시스템 절전 끄기 (뚜껑 닫고 충전기 꽂았을 때)
sudo pmset -c sleep 0

# 설정 확인
pmset -g | grep "^[ ]*sleep"
# → sleep    0 이어야 함
```

> 배터리로 전환되면 평소처럼 절전 동작합니다. `-c` = AC 전원일 때만 적용.

---

## 📊 GitHub Pages 대시보드

**라이브**: `https://siadaddy.github.io/youngs/` → 코인 트레이더 탭

- 매매 통계 (총 거래 / 승 / 패 / 승률 / 누적 손익)
- 누적 손익 차트 (Chart.js, 수익=초록 / 손실=빨강)
- 봇 상태 표시 (마지막 실행 시각 기준 🟢≤5분/🟡≤30분/🔴>30분)
- 현재 보유 종목 실시간 표시
- 최근 50건 매매 이력 + AI 판단 이유
- 티커별 매매 성과 집계 테이블

---

## 📱 ntfy 알림

| 상황 | 알림 |
|------|------|
| 매수 완료 | 🟢 종목·단가·AI 이유 |
| 즉시 재매수 | 🟢 SELL 직후 BUY 신호 감지 시 |
| 매도 완료 | 🔴 종목·이유 |
| 손절 매도 | 🔴 긴급 |
| 익절 매도 | 🟡 |
| Daily Drawdown 한도 도달 | 🛑 긴급 — 당일 봇 정지 |
| IP 변경 | 🔴 긴급 — 빗썸 재등록 필요 |
| 오류 복구 | ⚠️ N회 실패 후 정상 재개 |

---

## 🚀 수동 실행

```bash
cd /Users/youngchulyu/바이브코딩/coin-trader

# 전체 실행
python3 main.py

# 잔고 확인
python3 -c "
from utils.bithumb_client import get_krw_balance
print(f'KRW 잔고: {get_krw_balance():,.0f}원')
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

---

## 🛠 설치

```bash
pip install pybithumb pandas numpy python-dotenv requests
```

---

## 📝 업데이트 로그

### 2026-04-11
- **5분 간격 전환**: 15분 → 5분 (96회/일 → 288회/일)
- **30분봉 전환**: 10분봉 → 30분봉 (minute30, RSI/ADX period 9→14)
- **익절 기준 조정**: +15% → +6% (빠른 수익 실현)
- **손절 기준 조정**: -7% → -4%
- **Daily Drawdown 보호 추가**: 일일 손실 -15,000원 초과 시 당일 봇 정지

### 2026-04-06
- **빗썸 전환 완료**: 업비트 → 빗썸 (pybithumb API 1.0)
- **SELL 직후 즉시 BUY 재탐색**: 매도 완료 후 같은 사이클 내 매수 기회 탐색
- **IP 알림 정리**: IP 정상이면 ntfy 스킵, 변경 시에만 빗썸 재등록 안내
- **맥북 절전 설정 가이드 추가**: `pmset -c sleep 0` 필수 설정

### 2026-04-03
- **analyzer.py 병렬화**: ThreadPoolExecutor(max_workers=5)
- **하드 타임아웃**: BaseException 서브클래스로 진짜 킬 스위치
- **price_guard.py 충돌 방지**: lock 파일 감지로 동시 매도 경쟁 방지

### 2026-04-02
- **변동성 돌파(VB) 전략 추가**: K=0.5, 최우선 매수 신호

### 2026-03-31
- **price_guard.py 추가**: 손절/익절 실시간 감시

### 2026-03-28
- 시스템 최초 구축

---

*최종 업데이트: 2026-04-11 | Powered by Groq + pybithumb + GitHub Pages*
