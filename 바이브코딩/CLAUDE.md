# 🤖 AI 자동화 시스템 — Claude Code 컨텍스트

> 이 파일은 Claude Code 세션 시작 시 빠른 파악용입니다. 마지막 업데이트: 2026-04-17

---

## 📦 프로젝트 구조

```
바이브코딩/              ← git root
├── ai-crew/            ← AI 뉴스레터 자동 생성 (07:00 KST 매일)
├── coin-trader/        ← AI 코인 자동매매 (5분마다)
├── 뉴스레터/            ← RSS 뉴스 수집 (06:40 KST 매일)
└── docs/               ← GitHub Pages 대시보드
    ├── youtube_playlist.py   ← YouTube Music 누적 플레이리스트
    ├── playlist_state.json   ← 플레이리스트 ID + 추가된 곡 목록
    ├── video_cache.json      ← 곡명→videoId 캐시
    ├── music.json            ← 오늘 추천곡
    └── trades.json           ← 코인 매매 기록
```

---

## 🔑 API 키 & 모델 전략

### ai-crew (`ai-crew/.env`)
- **LLM**: Gemini 우선(`gemini_client.py`) → 실패 시 Groq 폴백
  - Gemini: 키1(`AIzaSy...`) → 키2(`AQ.Ab8...`), 2.0-flash → 2.5-flash 순서
  - Groq: 키4개 라운드로빈 (Gemini 전체 실패 시)
- 뉴스레터·음악 큐레이터 모두 Gemini 우선

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

## 🐛 최근 수정된 주요 버그 & 변경사항 (2026-04-17)

### coin-trader
1. **익절 8%로 수정** (기존 6%): `.env` TAKE_PROFIT_PCT=8.0
2. **price_guard.py .env 핫리로드**: 데몬이 시작 시 .env 1회만 읽어서 설정 변경이 반영 안 됐던 버그
   - 수정: `global STOP_LOSS, TAKE_PROFIT`을 main() 최상단에 선언, while 루프마다 `load_dotenv(override=True)` + 재할당
3. **ai_advisor.py Gemini 폴백 강화**: 이중 키, 429 시 65초 대기

### ai-crew
4. **music_curator.py DOCS_PATH 버그**: `../../../docs` → `../../docs` (바이브코딩/docs로 정상 저장)
5. **music_curator.py JSON 복구**: `_extract_songs()` 추가 — 잘린 JSON도 완성된 객체만 파싱 후 추출
6. **음악 장르 개편**: 2000년대힙합·최신힙합·러닝업템포·K-pop·여성발라드 (각 15/10/25/25/25곡)
7. **gemini_client.py 전면 재작성**: Gemini 우선, Groq 폴백, 413 즉시 종료, 이중 Gemini 키

### YouTube Music
8. **누적 플레이리스트**: `docs/youtube_playlist.py` 전면 재작성
   - 고정 이름 "AI 추천 플레이리스트" 하나 유지
   - `docs/playlist_state.json`에 playlist_id + 추가된 곡 목록 영구 보관
   - 날마다 신곡만 추가 (중복 건너뜀)
   - 추가할 때마다 state 저장 → 할당량 초과 중단 후 이어서 실행 가능

---

## ⏳ 미완료 / 내일 할 일

- **YouTube Music 플레이리스트 완성**: 오늘 할당량 소진 (100회 검색 초과)
  - 내일 오후 4시 KST 이후 리셋
  - `cd ~/바이브코딩/docs && python youtube_playlist.py` 실행
  - 처음 실행 → "AI 추천 플레이리스트" 생성 + 오늘 음악 추가

---

## 🔍 빠른 상태 확인

```bash
# 코인 보유 현황
cat ~/바이브코딩/coin-trader/state.json

# 코인 로그 (최근)
tail -50 ~/바이브코딩/coin-trader/trader.log

# AI 크루 로그 (최근)
tail -50 ~/바이브코딩/ai-crew/crew.log

# 유튜브 플레이리스트 상태
cat ~/바이브코딩/docs/playlist_state.json

# 오늘 음악 곡수
python3 -c "import json; d=json.load(open('docs/music.json')); print(len(d['songs']), '곡')"
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
| `ai-crew/agents/music_curator.py` | 음악 큐레이터 (Gemini→Groq, JSON 복구) |
| `coin-trader/price_guard.py` | 손절/익절 30초 감시 데몬 |
| `coin-trader/agents/ai_advisor.py` | 코인 AI 판단 (Groq→Gemini) |
| `docs/youtube_playlist.py` | YouTube 플레이리스트 관리 |
| `docs/playlist_state.json` | YouTube 플레이리스트 ID + 추가된 곡 |
