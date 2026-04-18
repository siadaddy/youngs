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
│           price_guard.py도 30초마다 독립 감시 (이중화)
├─ Step 4: 빗썸 KRW 마켓 거래대금 상위 20개 종목 선별
├─ Step 5: 각 종목 30분봉 OHLCV → RSI / MACD / 볼린저밴드 / ADX / 변동성돌파 계산
│           (ThreadPoolExecutor max_workers=5 병렬 처리)
├─ Step 6: 전역 쿨다운 체크 → 손절 후 2h 동안 모든 BUY 금지
├─ Step 7: Groq AI 판단 → BUY(종목명) / SELL / HOLD + 한국어 이유
│           쿨다운 종목 목록 전달 → AI가 제외 후 판단
├─ Step 8: 주문 실행 (빗썸 시장가, 최소금액 5,000원 체크)
│   └─ SELL 직후 → 전역 쿨다운 없을 때만 즉시 BUY 재판단
├─ Step 9: state.json 업데이트
├─ Step 10: ntfy 결과 알림
└─ Step 11: docs/trades.json 업데이트 → GitHub Pages push
```

---

## 🗂 파일 구조

```
coin-trader/
├── main.py                 ← 오케스트레이터 (5분 간격)
├── price_guard.py          ← 실시간 가격 감시 (30초 간격, 손절/익절 + 쿨다운 등록)
├── run_trader.sh           ← launchd 실행 스크립트
├── state.json              ← 보유 종목·매수가·수량 (재시작 시 복원)
├── cooldown.json           ← 손절 후 쿨다운 (종목별 3h + 전역 _global 2h)
├── drawdown.json           ← 일일 손실 누적 추적 (자정 자동 초기화)
├── ip.txt                  ← 마지막 확인 공인 IP (변경 감지용)
├── trader.log              ← 실행 로그
├── agents/
│   ├── analyzer.py         ← 거래량 상위 20개 + 30분봉 기술적 지표 계산 (병렬)
│   ├── ai_advisor.py       ← Groq AI 판단 (key1→2→3→4 폴백, 외국어 필터)
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
GROQ_API_KEY=...            # 폴백 체인 — key1 실패 시 key2→3→4 순서로 전환
GROQ_API_KEY_2=...
GROQ_API_KEY_3=...
GROQ_API_KEY_4=...
GEMINI_API_KEY=...          # Groq 전체 소진 시 폴백
GEMINI_API_KEY_2=...
MAX_INVEST_KRW=100000       # 최대 투자금액 (원)
STOP_LOSS_PCT=4.0           # 자동 손절 기준 (%)
TAKE_PROFIT_PCT=8.0         # 자동 익절 기준 (%)
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
6. **SELL 직후 재탐색**: 전역 쿨다운 없을 때만 — 매도 완료 즉시 AI 재판단 → BUY 신호 있으면 즉시 매수
7. **수익 보호**: 보유 수익률 +5% 이상이면 교체 금지
8. **횡보 금지**: ADX <10 + VB❌ 종목은 BUY 금지

---

## 🛡 안전장치

| 기능 | 내용 |
|------|------|
| 손절 | 매수가 대비 -4% 자동 매도 (price_guard 30초 감시 + main.py 5분 체크) |
| 익절 | 매수가 대비 +8% 자동 매도 |
| **손절 후 전역 쿨다운** | 손절 발동 시 2h 동안 **모든 종목 BUY 금지** (하락장 연속 손절 방지) |
| **손절 종목 쿨다운** | 손절 종목 3h 재진입 금지 |
| Daily Drawdown | 일일 누적 손실 -15,000원 초과 시 당일 봇 정지 (자정 초기화) |
| 매도 최소금액 체크 | qty × 현재가 < 5,000원이면 매도 보류 |
| IP 변경 감지 | 공인 IP 변경 시 ntfy 긴급 알림 (빗썸 API 재등록 안내) |
| Groq 폴백 | 429 발생 시 즉시 key1→2→3→4 폴백 체인, 모두 소진 시 Gemini 폴백 |
| 외국어 필터 | AI 응답에서 한자·일본어·아랍어·키릴 자동 제거 |
| DRY_RUN | 실제 주문 없이 전체 흐름 시뮬레이션 |
| 전체 타임아웃 | 10분 초과 시 강제 종료 (BaseException 하드킬) |

---

## 🔄 쿨다운 시스템 상세

```json
// cooldown.json 구조
{
  "SKL": "2026-04-19 15:33",    // 종목별: 손절 후 3h 동안 해당 종목 BUY 금지
  "_global": "2026-04-19 14:33" // 전역: 손절 후 2h 동안 모든 종목 BUY 금지
}
```

**동작 흐름**:
1. `price_guard.py` 손절 발동 → `add_cooldown(ticker)` 호출
2. `cooldown.json`에 종목(3h) + `_global`(2h) 동시 기록
3. `main.py` 다음 실행 → `is_global_cooldown()` → BUY 차단
4. 2h 후 전역 해제 → BUY 재개 / 3h 후 종목 해제 → 해당 종목 재진입 가능

---

## 💻 맥북 뚜껑 닫힘 설정 (필수)

```bash
# AC 전원 연결 시 시스템 절전 끄기
sudo pmset -c sleep 0

# 설정 확인
pmset -g | grep "^[ ]*sleep"
# → sleep    0 이어야 함
```

---

## 📊 GitHub Pages 대시보드

**라이브**: `https://siadaddy.github.io/youngs/` → 코인 트레이더 탭

- 매매 통계 (총 거래 / 승 / 패 / 승률 / 누적 손익)
- 누적 손익 차트 (Chart.js, 수익=초록 / 손실=빨강)
- 봇 상태 표시 (마지막 실행 시각 기준 🟢≤5분/🟡≤30분/🔴>30분)
- 현재 보유 종목 실시간 표시
- 최근 50건 매매 이력 + AI 판단 이유

---

## 📱 ntfy 알림

| 상황 | 알림 |
|------|------|
| 매수 완료 | 🟢 종목·단가·AI 이유 |
| 즉시 재매수 | 🟢 SELL 직후 BUY 신호 감지 시 |
| 매도 완료 | 🔴 종목·이유 |
| 손절 매도 | 🔴 긴급 + 쿨다운 시간 안내 |
| 익절 매도 | 🟡 |
| Daily Drawdown 한도 도달 | 🛑 긴급 — 당일 봇 정지 |
| IP 변경 | 🔴 긴급 — 빗썸 재등록 필요 |

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

# 쿨다운 현황
cat cooldown.json

# 로그 확인
tail -f trader.log
```

---

## ⚙️ launchd 관리

```bash
# 상태 확인
launchctl list | grep siadad

# cointrader 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.cointrader.plist
launchctl load ~/Library/LaunchAgents/com.siadad.cointrader.plist

# priceguard 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.priceguard.plist
launchctl load ~/Library/LaunchAgents/com.siadad.priceguard.plist
```

---

## 🛠 설치

```bash
pip install pybithumb pandas numpy python-dotenv requests
```

---

## 📝 업데이트 로그

### 2026-04-19
- **손절 후 즉시 재매수 방지 전면 개선**:
  - `price_guard.py` 손절 시 `cooldown.json` 미기록 버그 수정 → `add_cooldown()` 추가
  - 전역 쿨다운 `_global` 도입: 손절 후 2h 동안 **모든 종목 BUY 금지**
  - `is_global_cooldown()` 신규: main.py BUY 전 / SELL 후 재탐색 전 체크
  - 종목별 쿨다운: 2h → 3h 강화

### 2026-04-17
- **익절 기준 8%로 상향**: TAKE_PROFIT_PCT=6 → 8 (.env 수정)
- **price_guard.py .env 핫리로드**: 루프마다 `load_dotenv(override=True)` 재할당
- **ai_advisor.py Gemini 이중 키**: GEMINI_API_KEY_2 추가, 429 시 65초 대기

### 2026-04-14
- **시장 분석 NoneType 크래시 수정**: `pybithumb.get_tickers()` None 반환 시 장애 → None 차단 추가
- **Groq 429 즉시 전환**: 90초 대기 → 즉시 다음 키 전환으로 개선

### 2026-04-12
- **Groq 키 4개**: key1~4 폴백 체인
- **주문 가능 잔고 개선**: `available_krw` 직접 조회 후 75% 투자

### 2026-04-11
- **5분 간격 전환**: 15분 → 5분 (96회/일 → 288회/일)
- **30분봉 전환**: 10분봉 → 30분봉
- **손절 -4% / 익절 +6%** (이후 익절 +8% 상향)
- **Daily Drawdown 보호 추가**: 일일 손실 -15,000원 초과 시 당일 봇 정지

### 2026-04-06
- **빗썸 전환 완료**: 업비트 → 빗썸 (pybithumb API 1.0)
- **SELL 직후 즉시 BUY 재탐색** 추가

### 2026-04-03
- **analyzer.py 병렬화**: ThreadPoolExecutor(max_workers=5)
- **price_guard.py 추가**: 손절/익절 실시간 감시

### 2026-03-28
- 시스템 최초 구축

---

*최종 업데이트: 2026-04-19 | Powered by Groq + Gemini + pybithumb + GitHub Pages*
