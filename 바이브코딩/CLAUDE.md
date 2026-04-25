# 🤖 AI 자동화 시스템 — Claude Code 컨텍스트

> 이 파일은 Claude Code 세션 시작 시 빠른 파악용입니다. 마지막 업데이트: 2026-04-25 (2차)

---

## 📦 프로젝트 구조

```
/Users/youngchulyu/  (git root — GitHub Pages 서빙 기준)
├── docs/                      ← GitHub Pages (siadaddy.github.io/youngs)
│   ├── index.html             ← 메인 대시보드
│   ├── trades.json            ← 코인 매매 기록 + 블랙리스트 현황
│   ├── office_memory.json     ← AI 직원 학습 기록 (ai-crew + coin-trader 병합)
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
| `coin-trader/utils/office_export.py` | AI어드바이저 학습 기록 → docs/office_memory.json |

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
# 블랙리스트 현황
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

## 🎭 AI 사무실 탭 (index.html)

Canvas 픽셀아트 사무실. AI 직원 8명이 실시간으로 돌아다니며 학습 내용을 말풍선으로 표시.

### 직원 8명

| 직원 | 역할 | 특징 |
|------|------|------|
| 박기획 | 콘텐츠 기획자 | 네이비 정장, 금테 안경 |
| 최디자 | 이미지 디자이너 | 보라 머리, 핑크 의상 |
| 한뮤직 | 음악 큐레이터 | 헤드폰, 초록 후디 |
| AI주간트렌드 | 주간 분석가 | 은발, 청록 타이 |
| AI어드바이저 | 코인 어드바이저 | 로봇 발광 눈, 청록 밴드 |
| 뉴스기자 | 뉴스 수집가 | 중절모, 갈색 정장 |
| 이가드 | 시장 감시원 | 다크 유니폼, 레드 배지 |
| 리포터 | 일일 리포트 작성자 | 웨이브 머리, 오렌지 자켓 |

### 스프라이트 스펙
- 크기: **16열 × 24행** 픽셀아트 (`_PX=3`, 화면 48×72px)
- 2프레임 걷기 애니메이션
- 각 캐릭터 고유 팔레트 (16~18색)

### 행동 패턴 19가지
walk · home · coffee · window · stretch · think · rush · phone · sneak · dance ·  
read · wboard · snack · chat · printer · nap · patrol · report · water · exercise

- **회의 간격**: 2~3분 (meetTimer=1800~2700 @15fps)
- **말풍선**: office_memory.json 실데이터 반영

### office_memory.json
- `coin-trader/utils/office_export.py` → AI어드바이저 데이터
- `ai-crew/utils/office_export.py` → ai-crew 4명 데이터

---

## 🐛 최근 수정 이력

### 2026-04-25 (2차) — AI 사무실 낮/밤 자동 전환
- **낮/밤 자동 전환**: `render()`에서 매 프레임 `new Date().getHours()` 체크
  - 07~19시 ☀️ 낮 모드: 원목 바닥, 맑은 하늘 창문, 원목 책상·회의 테이블
  - 19~07시 🌙 밤 모드: 네온 그리드 바닥, 도시 야경, 다크 카본 책상
- **시계 표시**: 우상단 `☀️ 13:25` / `🌙 22:10` 실시간 표시
- **우측 데이터 패널**: AI어드바이저 현황 + 오늘의 뉴스 + 성장 랭킹 HTML 오버레이

### 2026-04-25 (1차) — AI 사무실 사이버펑크 업그레이드
- 배경: 원목 → 다크 네이비 + 네온 그리드
- 중앙 테이블: 원목 → 홀로그래픽 AI 브리핑 LIVE 패널
- 말풍선: 글래스모피즘 + 캐릭터 컬러 glow 보더
- 이름 뱃지: 네온 glow 강화
- 바닥 반사 효과 추가

### 2026-04-25 — AI 직원 자기학습 시스템 구현
- `ai-crew/utils/agent_memory.py`: diary, persona, growth_score 함수 추가
- `coin-trader/utils/agent_memory.py`: AI어드바이저 학습 엔진
- 각 에이전트 업무 완료 후 LLM 자기반성 → 1문장 일기 저장
- 5건+ 일기 + 7일 경과 시 페르소나 자동 재작성
- index.html: Lv.N 성장 점수 + 일기 말풍선 반영

### 2026-04-25 — AI 사무실 고도화
- 스프라이트: 10×16 @ _PX=4 → **16×24 @ _PX=3**
- 행동 패턴: 11가지 → **19가지** 확장
- 회의 빈도: 23초 → **2~3분**으로 완화

### 2026-04-23 — AI 사무실 탭 & 전면 버그 수정
- Canvas 픽셀아트 AI 사무실 탭 신규 추가 (8명, 10가지 행동)
- office_memory.json 실데이터 연동
- price_guard.py: register_stop_loss, record_loss, trailing_stop 누락 수정
- executor.py: force 플래그, 잔고 3회 재시도
- analyzer.py: ADX NaN 수정, 120초 타임아웃
- ai_advisor.py: RSI<20 점수 0→-5
- blacklist.py: add_successful_trade() 추가
- 웹사이트: AI 직원 5명→8명

### 2026-04-21 — 전면 개선
- buy_market_order 버그 수정
- 학습 블랙리스트 신규 구축
- MAX_INVEST 10만→5만, TAKE_PROFIT 8%→5%

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
| `ai-crew/utils/office_export.py` | ai-crew 4명 학습 기록 → office_memory.json |
| `coin-trader/price_guard.py` | 손절/익절 30초 감시 데몬 |
| `coin-trader/main.py` | 코인 AI 매매 오케스트레이터 |
| `coin-trader/agents/ai_advisor.py` | 코인 AI 판단 (Groq→Gemini) |
| `coin-trader/utils/blacklist.py` | 📚 학습 블랙리스트 엔진 |
| `coin-trader/utils/office_export.py` | AI어드바이저 학습 기록 → office_memory.json |
| `coin-trader/blacklist.json` | 손절 학습 데이터 영구 저장소 |
| `docs/trades.json` | 코인 매매 기록 + 블랙리스트 (GitHub Pages 서빙) |
| `docs/office_memory.json` | AI 직원 학습 기록 통합 (GitHub Pages 서빙) |
