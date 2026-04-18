# 🤖 AI 자동화 시스템 — Claude Code 컨텍스트

> 이 파일은 Claude Code 세션 시작 시 빠른 파악용입니다. 마지막 업데이트: 2026-04-19

---

## 📦 프로젝트 구조

```
바이브코딩/              ← git root
├── ai-crew/            ← AI 뉴스레터 자동 생성 (07:00 KST 매일)
├── coin-trader/        ← AI 코인 자동매매 (5분마다)
├── 뉴스레터/            ← RSS 뉴스 수집 (06:40 KST 매일)
└── docs/               ← GitHub Pages 대시보드
    ├── youtube_playlist.py   ← YouTube Music 누적 플레이리스트
    ├── playlist_state.json   ← 플레이리스트 ID + 추가된 곡 목록 (57곡 누적)
    ├── video_cache.json      ← 곡명→videoId 캐시 (119곡, GitHub Pages 서빙)
    ├── music.json            ← 최신 추천곡 (주 1회 갱신)
    └── trades.json           ← 코인 매매 기록
```

---

## 🔑 API 키 & 모델 전략

### ai-crew (`ai-crew/.env`)
- **LLM**: Gemini 우선(`gemini_client.py`) → 실패 시 Groq 폴백
  - Gemini 2.5-flash 우선 (2.0-flash는 RPM 429 상시 발생으로 스킵)
  - 키1(`AIzaSy...`) → 키2(`AQ.Ab8...`) 순서
  - Groq: 키 4개 라운드로빈 (Gemini 전체 실패 시)
- 뉴스레터·AI 에이전트: `ask_gemini()` (Gemini 우선, 2.0→2.5 폴백)
- 음악 큐레이터: `ask_gemini25_first()` (2.5-flash 직접, 반복 호출 많으므로)

### coin-trader (`coin-trader/.env`)
- **LLM**: Groq 우선(`ai_advisor.py`) → 실패 시 Gemini 폴백
  - Groq: 키1→2→3→4 순서
  - Gemini: 키1→키2, 429 시 65초 대기
- **매매 설정**: 손절 -4% / 익절 +8% / 일일손실한도 -15,000원 / 투자금 10만원
- **DRY_RUN=false** (실제 매매 중)

---

## ⚙️ 실행 중인 launchd 서비스

| plist | 역할 | 주기 |
|-------|------|------|
| com.siadad.newsletter | 뉴스 RSS 수집 | 매일 06:40 |
| com.siadad.aicrew | AI 뉴스레터 생성 | 매일 07:00 |
| com.siadad.cointrader | 코인 매매 (main.py) | 5분마다 |
| com.siadad.priceguard | 손절/익절 감시 (price_guard.py) | 상시 (30초 루프) |
| com.siadad.dailyreport | 일일 리포트 | 매일 08:30 |

**launchd 관리**:
```bash
launchctl list | grep siadad
launchctl unload ~/Library/LaunchAgents/com.siadad.cointrader.plist
launchctl load ~/Library/LaunchAgents/com.siadad.cointrader.plist
```

---

## 🐛 최근 수정된 주요 버그 & 변경사항

### 2026-04-19

**coin-trader — 손절 후 즉시 재매수 방지 전면 개선**
- 문제: price_guard가 손절해도 cooldown.json 미기록 → 30분 뒤 main.py가 즉시 재매수
- 문제2: 종목별 쿨다운만 있고 전역 쿨다운 없음 → 다른 종목 즉시 매수 가능
- `price_guard.py`: 손절 발동 시 `add_cooldown()` 추가 (종목 3h + `_global` 2h)
- `main.py`: BUY 전 `is_global_cooldown()` 체크 → 전역 쿨다운 중이면 BUY 차단
- `main.py`: SELL 후 즉시 재탐색도 전역 쿨다운 시 스킵
- 종목별 쿨다운: 2h → 3h 강화

**music.html — Chrome 오토플레이 차단 수정**
- 문제: `await searchVideo()` → `await waitReady()` 후 `loadVideoById()` → Chrome이 사용자 제스처로 불인정
- 수정: 페이지 로드 시 `video_cache.json` 미리 fetch (fire-and-forget)
- 클릭 시 `_vidCache[cacheKey]` 동기 참조 → 캐시 히트 + ytReady 시 즉시 `loadVideoById()` (await 없음)
- 캐시 미스만 async fallback (검색 표시기 표시)

### 2026-04-18

**music.html — 갤럭시 & 플레이리스트 전면 개편**
- 별 배치: Box-Muller Gaussian 분포, 3개 나선팔
- `playRingSpr` → `galaxyGroup`으로 이동 (회전 시 위치 동기화)
- 플레이리스트 패널: `music.json` 전체 곡 자동 표시, 클릭 재생, 현재 곡 하이라이트
- 7개 장르 × 색상 매핑 (GENRE 맵)

**ai-crew — 음악 수집 개편**
- 7개 장르 × 10곡 = 70곡, 주 1회 수집 (`_should_run_music()` — 7일 미만이면 스킵)
- `ask_gemini25_first()` 신규: 2.5-flash 직접, 2.0-flash 완전 스킵
- YouTube Music 누적 플레이리스트: `playlist_state.json`으로 신곡만 추가

### 2026-04-17

**coin-trader**
- 익절 8%로 수정 (기존 6%)
- price_guard .env 핫리로드 수정
- ai_advisor Gemini 이중 키 + 429 시 65초 대기

**ai-crew**
- music_curator DOCS_PATH 버그 수정
- JSON 복구 로직 추가 (`_extract_songs()`)
- gemini_client.py 전면 재작성

---

## 🎵 음악 큐레이터 현황

### 장르 구성 (7개 × 10곡 = 70곡, 주 1회)
| 장르 | 색상 | 내용 |
|------|------|------|
| 2000s힙합 | 황금 #ffd60a | 2000~2009 미국/영국 힙합 |
| 최신힙합 | 보라 #9b5de5 | 2020년 이후 해외 힙합 |
| 러닝업템포 | 민트 #00f5a0 | BPM 140~180 운동용 |
| K-pop | 핑크 #ff6b9d | 최근 3년 남자 아이돌/솔로 |
| 여성발라드 | 하늘 #74b9ff | 한국/팝 여성 보컬 발라드 |
| 걸그룹 | 빨강 #ff4d6d | 최근 3년 K-pop 걸그룹 |
| 최신곡 | 시안 #00d4ff | 2024~2025 해외 팝/R&B |

### video_cache.json
- 119곡 캐시 (`"아티스트|제목": "videoId"` 형식)
- `docs/video_cache.json` → GitHub Pages에서 바로 fetch 가능
- music.html이 페이지 로드 시 미리 받아둠 → 클릭 즉시 동기 재생

---

## 🛡 코인 트레이더 쿨다운 시스템

```json
// cooldown.json 구조
{
  "SKL": "2026-04-19 15:33",    // 종목별 쿨다운 (3h) — 같은 종목 재진입 금지
  "_global": "2026-04-19 14:33" // 전역 쿨다운 (2h) — 어떤 종목도 BUY 금지
}
```

손절 발동 → `add_cooldown()` (price_guard & main 양쪽) → 2h 전역 + 3h 종목 쿨다운

---

## 🔍 빠른 상태 확인

```bash
# 코인 보유 현황
cat ~/바이브코딩/coin-trader/state.json

# 코인 쿨다운 현황
cat ~/바이브코딩/coin-trader/cooldown.json

# 코인 로그 (최근)
tail -50 ~/바이브코딩/coin-trader/trader.log

# AI 크루 로그 (최근)
tail -50 ~/바이브코딩/ai-crew/crew.log

# 유튜브 플레이리스트 상태
cat ~/바이브코딩/docs/playlist_state.json

# 음악 수집 마지막 날짜 & 곡수
python3 -c "import json; d=json.load(open('docs/music.json')); print(d['updated'], '/', len(d['songs']), '곡')"
```

---

## 🌐 GitHub Pages

**라이브**: https://siadaddy.github.io/youngs/

자동 push: `ai-crew/main.py` 완료 시, `coin-trader/main.py` 매매 시, `price_guard.py` 손절/익절 시

---

## 📁 핵심 파일 위치

| 파일 | 역할 |
|------|------|
| `ai-crew/utils/gemini_client.py` | Gemini/Groq 통합 클라이언트 (ai-crew 전용) |
| `ai-crew/agents/music_curator.py` | 음악 큐레이터 (7장르×10곡, 주1회, Gemini25→Groq) |
| `coin-trader/price_guard.py` | 손절/익절 30초 감시 데몬 + cooldown 등록 |
| `coin-trader/main.py` | 코인 AI 매매 오케스트레이터 + 전역 쿨다운 체크 |
| `coin-trader/agents/ai_advisor.py` | 코인 AI 판단 (Groq→Gemini) |
| `docs/youtube_playlist.py` | YouTube 플레이리스트 관리 |
| `docs/playlist_state.json` | YouTube 플레이리스트 ID + 추가된 곡 (57곡) |
| `docs/video_cache.json` | 곡→videoId 캐시 (119곡, GitHub Pages 서빙) |
| `docs/music.html` | 갤럭시 3D 뮤직 유니버스 (Three.js, YouTube 인앱 재생) |
