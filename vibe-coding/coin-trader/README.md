# 🤖 AI 코인 자동매매 시스템

> 빗썸 KRW 마켓에서 AI가 종목 선정·매수·매도를 완전 자동화하는 트레이딩 시스템

**실행 환경**: MacBook (launchd) — 30분마다 자동 실행 (48회/일)
**투자금**: 5만원 | **실전 운용 중** (DRY_RUN=false)

---

## 📋 시스템 개요

빗썸 KRW 전체 마켓에서 24h 거래대금 상위 종목을 분석하고,
Groq AI(Llama 3.3 70B)가 기술적 지표를 바탕으로 BUY / SELL / HOLD를 판단합니다.

**핵심 보호 장치**: 손절 발생 시 해당 종목을 학습·기록하고, 반복 손절 종목은 자동으로 차단합니다.

---

## 🕐 자동화 흐름

```
매 :00 / :30 (하루 48회)
│
├─ Step 0: 이전 실패 감지 + IP 변경 체크
├─ Step 0-1: Daily Drawdown 체크 → 일일 손실 한도 초과 시 당일 봇 정지
├─ Step 0-2: 📚 블랙리스트 초기화 (없으면 거래 기록에서 자동 구성)
├─ Step 1: state.json 로드 → 현재 보유 종목 확인
├─ Step 1-1: orphaned 포지션 감지 및 정리
├─ Step 2: 고점 갱신 + 손절/익절/트레일링스탑/강제청산 체크
│           price_guard.py도 30초마다 독립 감시 (이중화)
├─ Step 3: 시장 분석
│   ├─ 빗썸 24h 거래대금 상위 선별
│   ├─ 🚫 블랙리스트·스테이블코인 제외
│   ├─ 🚫 24h 거래대금 20억원 미만 제외
│   └─ 30분봉 RSI·MACD·볼린저밴드·ADX·VB 계산 (병렬 5개)
├─ Step 3-1: 쿨다운 종목 목록 조회
├─ Step 4: Groq AI 판단 → BUY / SELL / HOLD + 한국어 이유
├─ Step 4-1: AI 오판 차단 (실제 수익률 양수인데 손절 SELL → HOLD 강제 전환)
├─ Step 5: 전역 쿨다운 체크 → BUY 차단 여부 결정
├─ Step 6: 주문 실행 (빗썸 시장가)
│   ├─ SELL 후 → 기회교체 쿨다운 등록 + 시장 재수집 + 즉시 BUY 재판단
│   └─ 스테이블코인·블랙리스트 하드차단 (executor 레벨)
├─ Step 7: 결과 알림 (ntfy)
└─ Step 8: trades.json (블랙리스트 포함) → GitHub Pages push
```

---

## 🗂 파일 구조

```
coin-trader/
├── main.py                 ← 오케스트레이터 (30분 간격)
├── price_guard.py          ← 실시간 가격 감시 (30초, 손절/익절/쿨다운)
├── state.json              ← 보유 종목·매수가·수량·고점 (재시작 시 복원)
├── cooldown.json           ← 손절 후 쿨다운 (종목 6h + 전역 _global 4h)
├── blacklist.json          ← 📚 반복 손절 학습 데이터 (영구 저장)
├── drawdown.json           ← 일일 손실 누적 (자정 자동 초기화)
├── ip.txt                  ← 마지막 확인 공인 IP (변경 감지용)
├── trader.log              ← 실행 로그
├── agents/
│   ├── analyzer.py         ← 거래량 상위 + 30분봉 기술 지표 계산 (병렬)
│   ├── ai_advisor.py       ← Groq AI 판단 (key1→2→3→4 폴백)
│   └── executor.py         ← 빗썸 시장가 주문 + 스테이블코인·블랙리스트 하드차단
└── utils/
    ├── bithumb_client.py   ← pybithumb 래퍼 (잔고·현재가·매수·매도)
    ├── blacklist.py        ← 📚 학습 블랙리스트 엔진
    └── upbit_client.py     ← 레거시 (미사용)
```

---

## 🔧 .env 설정

```env
BITHUMB_ACCESS_KEY=...         # 빗썸 API 1.0 키 (주문 권한 필수)
BITHUMB_SECRET_KEY=...
GROQ_API_KEY=...               # 폴백 체인 — 429 시 즉시 key2→3→4 전환
GROQ_API_KEY_2=...
GROQ_API_KEY_3=...
GROQ_API_KEY_4=...
GEMINI_API_KEY=...             # Groq 전체 소진 시 폴백
GEMINI_API_KEY_2=...
MAX_INVEST_KRW=50000           # 최대 투자금액 (원)
STOP_LOSS_PCT=4.0              # 자동 손절 기준 (%)
TAKE_PROFIT_PCT=5.0            # 자동 익절 기준 (%)
TRAILING_STOP_PCT=2.5          # 트레일링스탑: 고점 대비 하락 기준 (%)
TRAILING_ACTIVATE_PCT=3.0      # 트레일링스탑: 활성화 수익률 기준 (%)
MAX_HOLD_HOURS=8.0             # 강제청산: 최대 보유 시간 (h)
DAILY_LOSS_LIMIT_KRW=-7500    # 일일 손실 한도 (원, 초과 시 당일 봇 정지)
DRY_RUN=false                  # true=시뮬레이션, false=실제 주문
NTFY_TOPIC=siadad-aicrew
```

---

## 🧠 기술적 지표 & 스코어링

| 지표 | 설정 | 매수 점수 | 매도 점수 |
|------|------|----------|----------|
| RSI | 14봉 (30분봉) | 20~35: +2 / 35~50: +1 / **<20: -5 (급락 중, BUY 강차단)** | >65: -1 / >75: -2 |
| MACD | 12/26/9 | 골든크로스: +2 / 상승: +1 | 데드크로스: -2 / 하락: -1 |
| 볼린저밴드 | 20/2σ | 하단: +2 / 중하단: +1 | 상단: -2 / 중상단: -1 |
| ADX | 14봉 | **≥20** 추세 있음 (매수 허용) | <20 횡보 (매수 금지) |
| **변동성 돌파(VB)** | K=0.5 (일봉) | **거래량+20% 동반: +2 / 미동반: +1** | — |

**변동성 돌파 공식**: `오늘 시가 + (전일 고가 - 전일 저가) × 0.5`

---

## 🛡 안전장치 전체

| 기능 | 기준 |
|------|------|
| 손절 | 매수가 대비 -4% 자동 매도 |
| 익절 | 매수가 대비 +5% 자동 매도 |
| 트레일링스탑 | +3% 수익 시 활성 → 고점 대비 -2.5% 하락 시 매도 |
| 강제청산 | 8시간 이상 보유 + 수익률 -1% 이하 → 강제 매도 |
| **📚 학습 블랙리스트** | 손절 2회→3일 / 3회→7일 / 4회→14일 / 5회+→30일 차단 |
| 스테이블코인 차단 | USDT·USDC·DAI·BUSD·TUSD 등 하드코드 BUY 금지 |
| 종목 쿨다운 | 손절 후 해당 종목 **6시간** 재진입 금지 |
| 전역 쿨다운 | 손절 후 모든 종목 **4시간** BUY 금지 |
| 기회교체 쿨다운 | 기회교체 SELL 후 해당 종목 **2시간** 재진입 금지 |
| Daily Drawdown | 일일 손실 -7,500원 초과 시 당일 봇 정지 |
| 거래대금 필터 | 24h 거래대금 20억원 미만 잡코인 제외 |
| buy_market_order 수정 | executor 계산 투자금 그대로 사용 (avail_krw×0.75 오버라이드 버그 수정) |
| AI 오판 차단 | 실제 수익률 양수인데 AI가 손절 SELL 지시 → HOLD 강제 전환 |
| 즉시 재판단 시 재수집 | SELL 후 동일 시장 데이터가 아닌 새 데이터로 AI 재판단 |
| IP 변경 감지 | 공인 IP 변경 시 ntfy 긴급 알림 (빗썸 API 재등록 안내) |
| Groq 폴백 | 429 즉시 key1→2→3→4 전환, 전체 소진 시 Gemini 폴백 |
| 전체 타임아웃 | 10분 초과 시 SIGALRM 강제 종료 |

---

## 📚 학습 블랙리스트 시스템

```
손절 1회 → 기록만 (6h 쿨다운 적용)
손절 2회 → blacklist.json 등록, 3일간 분석·매수 차단
손절 3회 → 7일 차단
손절 4회 → 14일 차단
손절 5회+ → 30일 차단
```

**3중 차단 구조**:
1. `analyzer.py` — 분석 대상에서 제외 (AI가 아예 보지 못함)
2. `ai_advisor.py` — 프롬프트에 블랙리스트 명시 + 쿨다운 종목 스코어링에서 필터
3. `executor.py` — 하드코드 BUY 차단 (분석 통과해도 막힘)

**수익 학습 복구 (add_successful_trade)**:
- 블랙리스트 등록 종목이 수익 3회 달성 시 → 손절 카운트 1 감소
- 반복 수익으로 신뢰 회복 시 점진적 차단 해제 가능

```bash
# 블랙리스트 현황 확인
python3 -c "
from utils.blacklist import get_summary
for line in get_summary(): print(line)
"
```

---

## 🔄 쿨다운 시스템

```json
// cooldown.json 구조
{
  "NCT": "2026-04-25 23:55",   // 손절 종목 쿨다운 (6h)
  "FORT": "2026-04-24 12:49",  // 손절 종목 쿨다운 (6h)
  "_global": "2026-04-21 16:49" // 전역 쿨다운 (4h) — 어떤 종목도 BUY 금지
}
```

---

## 📋 AI 매매 판단 규칙 (요약)

**매수 조건**:
1. USDT/USDC 등 스테이블코인 → 절대 BUY 금지
2. RSI < 20 → BUY 금지 (급락 추세)
3. VB✅ + 거래량+20% + 점수+4 이상 → BUY 최우선
4. 점수+5 이상 + ADX≥25 + MACD 상승/골든 → BUY 적극 고려
5. ADX < 20 + VB❌ → BUY 금지 (횡보장)
6. 거래량 -30% 이하 → BUY 금지

**보유 시간별 매도 기준**:
- 4h 미만: 점수 -3 이하 or RSI72+ + 데드크로스 → SELL
- 4~6h: 점수 -1 이하 or RSI70+ + 하락 → SELL
- 6h+, 수익률 0% 이하: 반등 신호 없으면 SELL

**기회 교체 (매우 신중)**:
- 90분 이상 + 수익률 -3% 미만 + 점수 -2 이하 + 다른 종목 VB✅+점수+5+ADX25 → 교체

---

## 💻 맥북 설정 (필수)

```bash
# AC 전원 연결 시 절전 비활성화
sudo pmset -c sleep 0

# 확인
pmset -g | grep "^[ ]*sleep"  # → sleep 0 이어야 함
```

---

## 🚀 수동 실행

```bash
cd /Users/youngchulyu/바이브코딩/coin-trader

# 전체 실행
python3 main.py

# 블랙리스트 현황
python3 -c "from utils.blacklist import get_summary; [print(l) for l in get_summary()]"

# 쿨다운 현황
cat cooldown.json

# 보유 현황
cat state.json

# 로그 확인
tail -f trader.log
```

---

## ⚙️ launchd 관리

```bash
launchctl list | grep siadad

# cointrader 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.cointrader.plist
launchctl load   ~/Library/LaunchAgents/com.siadad.cointrader.plist

# priceguard 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.priceguard.plist
launchctl load   ~/Library/LaunchAgents/com.siadad.priceguard.plist
```

---

## 🛠 설치

```bash
pip install pybithumb pandas numpy python-dotenv requests
```

---

## 📝 업데이트 로그

### 2026-04-23 (현재) — 전면 버그 수정 & 학습 강화

**price_guard.py — 핵심 버그 3개 수정**
- 실시간 손절 시 `register_stop_loss()` 누락 → 블랙리스트 학습이 30분 사이클에서만 동작하던 문제 수정
- 실시간 손절 시 `record_loss()` 누락 → 일일 손실 한도(-7,500원)가 실시간 손절엔 작동 안 하던 문제 수정
- TAKE_PROFIT 기본값 `8.0` → `5.0` 수정 (.env 없을 시 잘못된 값 사용)
- **트레일링스탑 로직 추가** — 30분 main.py에만 있던 트레일링스탑을 30초 price_guard에도 적용
- 매도 3회 자동 재시도 로직 추가

**executor.py**
- `force` 플래그 추가 — 손절/강제청산 시 5,000원 최소금액 체크 무시
- 잔고 조회 3회 재시도 + state.json 폴백

**analyzer.py**
- ADX 계산 Inf/NaN 오류 수정 (평탄 가격 데이터 시 divide-by-zero)
- 병렬 분석 120초 전체 타임아웃 추가 (미완료 스레드 취소 후 완료분만 사용)

**ai_advisor.py**
- RSI < 20 점수: `0 (중립)` → `-5 (BUY 강차단)` — 급락 중 VB 신호로 BUY 허용되던 버그 수정
- 쿨다운 종목 스코어링 단계에서 사전 필터링 추가

**utils/blacklist.py**
- `add_successful_trade()` 신규 — 블랙리스트 종목 수익 3회 달성 시 손절 카운트 1 감소

**main.py**
- 실제 PnL 계산: 추정값(`invest_krw × STOP_LOSS%`) → 실가 × 수량으로 정확한 계산
- `force_sell` 플래그: stop_loss / trailing_stop / time_exit 시 자동 적용
- `add_successful_trade()` 호출: 익절 / 트레일링스탑 매도 시 수익 학습 기록

---

### 2026-04-21
- **학습 블랙리스트**: `utils/blacklist.py` 신규 — 손절 횟수 누적 학습, 자동 차단
- **투자금 축소**: 10만원 → 5만원 / 일일한도 -15,000원 → -7,500원
- **buy_market_order 버그 수정**: amount_krw 파라미터 무시 버그 수정
- **기회교체 쿨다운**: 기회교체 SELL 후 2시간 해당 종목 재진입 금지
- **즉시 재판단 시 데이터 재수집**: SELL 후 시장 데이터 새로 가져와서 AI 재판단
- **스테이블코인 하드차단**: executor 코드 레벨 차단 (AI 무시해도 막힘)
- **RSI<20 중립**: 급락 중 극단적 과매도는 반등 신호 아님 → 0점 처리
- **VB 조건 강화**: 거래량+20% 동반 시 +2 / 미동반 시 +1
- **ADX 기준 강화**: 15→20 이상
- **거래대금 필터**: 24h 20억원 미만 잡코인 분석 제외

### 2026-04-21 (이전)
- **트레일링스탑**: +3% 활성 → 고점 대비 -2.5% 하락 시 매도
- **8시간 강제청산**: MAX_HOLD_HOURS=8
- **쿨다운 강화**: 종목 3h→6h / 전역 2h→4h
- **익절 수정**: +8% → +5%

### 2026-04-19
- **손절 후 즉시 재매수 방지**: stale cooldown 버그 수정 → fresh 쿨다운 사용

### 2026-04-17
- **ai_advisor.py Gemini 이중 키**: GEMINI_API_KEY_2 추가

### 2026-04-14
- **시장 분석 NoneType 크래시 수정**
- **Groq 429 즉시 전환**: 90초 대기 → 즉시 다음 키

### 2026-04-12
- **빗썸 전환 완료**: 업비트 → pybithumb

### 2026-04-03
- **변동성 돌파(VB)**: K=0.5, analyzer.py 병렬화

### 2026-03-28
- 시스템 최초 구축

---

*최종 업데이트: 2026-04-23 | Powered by Groq + Gemini + pybithumb + GitHub Pages*
