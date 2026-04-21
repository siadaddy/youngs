# 🤖 AI 자동화 시스템 — Claude Code 컨텍스트

> 이 파일은 Claude Code 세션 시작 시 빠른 파악용입니다. 마지막 업데이트: 2026-04-21

---

## 📦 프로젝트 구조

```
/Users/youngchulyu/  (git root — GitHub Pages 서빙 기준)
├── docs/                      ← GitHub Pages (siadaddy.github.io/youngs)
│   ├── index.html             ← 메인 대시보드
│   ├── trades.json            ← 코인 매매 기록 + 블랙리스트 현황
│   ├── content.json / archive.json / music.json
│   └── images/
└── 바이브코딩/
    ├── ai-crew/               ← AI 뉴스레터 (07:00 KST 매일)
    ├── coin-trader/           ← AI 코인 자동매매 (30분마다)
    ├── 뉴스레터/               ← RSS 수집 (06:40 KST 매일)
    └── CLAUDE.md              ← 이 파일
```

> ⚠️ git root는 `/Users/youngchulyu/` 이고 바이브코딩/이 아님.
> `git -C /Users/youngchulyu/ add docs/index.html` 처럼 절대경로 사용.

---

## 🔑 API 키 & 모델 전략

### ai-crew (`ai-crew/.env`)
- **LLM**: Gemini 우선 → 실패 시 Groq 폴백
  - Gemini 2.5-flash 우선 (키1 → 키2)
  - Groq: 키 4개 라운드로빈 (Gemini 전체 실패 시)

### coin-trader (`coin-trader/.env`)
- **LLM**: Groq 우선 → 실패 시 Gemini 폴백
  - Groq: key1→2→3→4, 429 즉시 전환
  - Gemini: 키1→키2, 429 시 65초 대기
- **현재 매매 설정**:
  - 투자금: **5만원** (MAX_INVEST_KRW=50000)
  - 손절: **-4%** (STOP_LOSS_PCT=4.0)
  - 익절: **+5%** (TAKE_PROFIT_PCT=5.0)
  - 트레일링스탑: **+3% 활성 / -2.5% 트리거**
  - 강제청산: **8시간** 이상 보유 + -1% 이하
  - 일일손실한도: **-7,500원**
  - 종목 쿨다운: **6시간** / 전역 쿨다운: **4시간**
  - DRY_RUN=false (실제 매매 중)

---

## ⚙️ 실행 중인 launchd 서비스

| plist | 역할 | 주기 |
|-------|------|------|
| com.siadad.newsletter | 뉴스 RSS 수집 | 매일 06:40 |
| com.siadad.aicrew | AI 뉴스레터 생성 | 매일 07:00 |
| com.siadad.cointrader | 코인 매매 (main.py) | **30분마다** (:00/:30) |
| com.siadad.priceguard | 손절/익절 감시 (price_guard.py) | 상시 (30초 루프) |
| com.siadad.dailyreport | 일일 리포트 | 매일 08:30 |

```bash
launchctl list | grep siadad
launchctl unload ~/Library/LaunchAgents/com.siadad.cointrader.plist
launchctl load   ~/Library/LaunchAgents/com.siadad.cointrader.plist
```

---

## 🪙 코인 트레이더 핵심 구조

### 파일 역할

| 파일 | 역할 |
|------|------|
| `coin-trader/main.py` | 30분 오케스트레이터 + 블랙리스트 초기화 + 매매 실행 |
| `coin-trader/price_guard.py` | 30초 손절/익절 실시간 감시 데몬 |
| `coin-trader/agents/analyzer.py` | 거래대금 상위 선별 + 블랙리스트 제외 + 기술 지표 계산 |
| `coin-trader/agents/ai_advisor.py` | Groq AI 판단 (BUY/SELL/HOLD) |
| `coin-trader/agents/executor.py` | 시장가 주문 + 스테이블코인·블랙리스트 하드차단 |
| `coin-trader/utils/bithumb_client.py` | pybithumb 래퍼 |
| `coin-trader/utils/blacklist.py` | 📚 학습 블랙리스트 엔진 |

### 핵심 상태 파일

| 파일 | 내용 |
|------|------|
| `state.json` | 현재 보유 종목·매수가·수량·고점 |
| `cooldown.json` | 손절 쿨다운 (종목 6h + 전역 `_global` 4h) |
| `blacklist.json` | 📚 반복 손절 종목 학습 데이터 (영구) |
| `drawdown.json` | 일일 손실 누적 |
| `trader.log` | 실행 로그 |

---

## 📚 학습 블랙리스트 시스템

```
손절 1회 → 기록 (6h 쿨다운)
손절 2회 → 3일 차단
손절 3회 → 7일 차단
손절 4회 → 14일 차단
손절 5회+ → 30일 차단
```

- `register_stop_loss(ticker)` — main.py에서 stop_loss 이벤트 시 자동 호출
- `get_blacklisted_tickers()` — analyzer.py에서 분석 대상 제외
- `is_blacklisted(ticker)` — executor.py에서 하드차단

```bash
# 블랙리스트 현황 (현재)
python3 -c "
import sys; sys.path.insert(0,'.')
from utils.blacklist import get_summary
for l in get_summary(): print(l)
"
```

---

## 🛡 쿨다운 시스템

```json
// cooldown.json
{
  "FORT": "2026-04-24 12:49",   // 종목 쿨다운 (손절 후 6h)
  "_global": "2026-04-21 16:49" // 전역 쿨다운 (손절 후 4h)
}
```

---

## 🐛 최근 수정된 주요 버그 & 변경사항

### 2026-04-21 — 전면 개선

**버그 수정**
- `bithumb_client.buy_market_order()`: `amount_krw` 파라미터 무시 버그 수정
  (avail_krw × 0.75로 재계산하던 것 → 전달받은 금액 그대로 사용)
- 기회교체 SELL 후 쿨다운 미등록 버그 수정 (`_add_switch_cooldown()` 추가)
- 즉시 재판단 시 동일 데이터 재사용 문제 수정 (재판단 전 `analyzer.run()` 재호출)

**신규 기능**
- `utils/blacklist.py`: 손절 횟수 누적 학습, 자동 블랙리스트 등록
- 시작 시 블랙리스트 현황 로그 출력
- trades.json에 blacklist 필드 포함 (웹사이트 표시용)

**투자 파라미터**
- MAX_INVEST_KRW: 100000 → **50000**
- TAKE_PROFIT_PCT: 8.0 → **5.0**
- DAILY_LOSS_LIMIT_KRW: -15000 → **-7500**

**전략 강화**
- RSI < 20 → 중립 0점 (급락 추세, 반등 신호 아님)
- VB: 거래량+20% 동반 시 +2 / 미동반 +1
- ADX 기준: 15 → 20 이상
- 기회교체: -2% → -3%, 60분 → 90분, 조건 강화
- 스테이블코인 executor 하드차단

### 2026-04-21 (이전)
- 트레일링스탑 +3% 활성 / -2.5% 트리거
- 8시간 강제청산 (MAX_HOLD_HOURS=8)
- 쿨다운 강화: 종목 3h→6h / 전역 2h→4h

### 2026-04-19
- stale cooldown 버그 수정 (손절 직후 재매수 방지)

---

## 🔍 빠른 상태 확인

```bash
# 코인 보유 현황
cat ~/바이브코딩/coin-trader/state.json

# 블랙리스트 현황
cd ~/바이브코딩/coin-trader && python3 -c "
from utils.blacklist import get_summary
for l in get_summary(): print(l)"

# 쿨다운 현황
cat ~/바이브코딩/coin-trader/cooldown.json

# 코인 로그 (최근 50줄)
tail -50 ~/바이브코딩/coin-trader/trader.log

# AI 크루 로그
tail -50 ~/바이브코딩/ai-crew/crew.log

# 음악 수집 상태
python3 -c "import json; d=json.load(open('docs/music.json')); print(d['updated'], '/', len(d['songs']), '곡')"
```

---

## 🎵 음악 큐레이터 현황 (ai-crew)

### 장르 구성 (7개 × 10곡 = 70곡, 주 1회)

| 장르 | 내용 |
|------|------|
| 2000s힙합 | 2000~2009 미국/영국 힙합 |
| 최신힙합 | 2020년 이후 해외 힙합 |
| 러닝업템포 | BPM 140~180 운동용 |
| K-pop | 최근 3년 남자 아이돌/솔로 |
| 여성발라드 | 한국/팝 여성 보컬 발라드 |
| 걸그룹 | 최근 3년 K-pop 걸그룹 |
| 최신곡 | 2024~2025 해외 팝/R&B |

---

## 🌐 GitHub Pages

**라이브**: https://siadaddy.github.io/youngs/

- `ai-crew/main.py` 완료 시 자동 push
- `coin-trader/main.py` 매매 체결 시 자동 push
- `price_guard.py` 손절/익절 시 자동 push

---

## 📁 핵심 파일 위치

| 파일 | 역할 |
|------|------|
| `ai-crew/utils/gemini_client.py` | Gemini/Groq 통합 클라이언트 |
| `ai-crew/agents/music_curator.py` | 음악 큐레이터 (7장르×10곡, 주1회) |
| `coin-trader/price_guard.py` | 손절/익절 30초 감시 데몬 |
| `coin-trader/main.py` | 코인 AI 매매 오케스트레이터 |
| `coin-trader/agents/ai_advisor.py` | 코인 AI 판단 (Groq→Gemini) |
| `coin-trader/utils/blacklist.py` | 📚 학습 블랙리스트 엔진 |
| `coin-trader/blacklist.json` | 손절 학습 데이터 영구 저장소 |
| `docs/trades.json` | 코인 매매 기록 + 블랙리스트 (GitHub Pages 서빙) |
