# 🤖 youngchulyu — AI 자동화 프로젝트 모음

> MacBook 위에서 24시간 돌아가는 AI 자동화 시스템들

**라이브 대시보드**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)

---

## 📦 프로젝트 구성

| 프로젝트 | 설명 | 실행 주기 |
|---------|------|---------|
| [ai-crew](./ai-crew/) | AI 뉴스레터 자동 생성 (카드뉴스 5개 + 블로그 + 이미지 + 음악) | 매일 07:00 |
| [coin-trader](./coin-trader/) | AI 코인 자동매매 (빗썸 KRW 마켓) | 30분마다 + 30초 감시 |
| [뉴스레터](./뉴스레터/) | RSS 뉴스 자동 수집 & 카테고리 분류 | 매일 06:40 |
| [docs](./docs/) | GitHub Pages 대시보드 | — |

---

## 📰 ai-crew — AI 뉴스레터

RSS로 수집된 뉴스를 바탕으로 Gemini / Groq AI가 에디터픽 기사와 카드뉴스를 자동 생성합니다.

- **AI 모델**: Gemini 2.5-flash 우선 → Groq Llama 3.3 70B 폴백 (키 4개 라운드로빈)
- **이미지**: Pollinations.ai (Flux 모델), 실패 시 fallback 이미지 자동 대체
- **품질 검사**: 5단계 (블랙리스트 · 제목-본문 일관성 · 문장 품질 · 해시태그 위치 · 해시태그 수)
- **출력**: GitHub Pages 뉴스레터 탭 자동 게시

```
뉴스 수집(06:40) → AI 기사 작성(07:00) → 이미지 생성 → GitHub Pages 게시
```

→ [자세히 보기](./ai-crew/README.md)

---

## 🪙 coin-trader — AI 코인 자동매매

빗썸 KRW 마켓 상위 20개 종목을 분석해 Groq AI가 매매를 자동 실행합니다.

- **분석**: 30분봉 RSI · MACD · 볼린저밴드 · ADX · 변동성 돌파 (병렬 5개)
- **안전장치**: 손절 -4% / 익절 +5% / 트레일링스탑 +3%/-2.5% / 8h 강제청산 / Daily Drawdown -7,500원
- **학습 블랙리스트**: 반복 손절 종목 자동 차단 (2회→3일 / 5회+→30일)
- **알림**: ntfy 실시간 푸시 알림
- **대시보드**: 누적 손익 차트 · 봇 상태 · 매매 이력

```
매 :00/:30: 시장 분석 → AI 판단(BUY/SELL/HOLD) → 주문 실행 → 대시보드 업데이트
상시(30초): price_guard → 손절/익절/트레일링스탑 실시간 감시
```

→ [자세히 보기](./coin-trader/README.md)

---

## 📡 뉴스레터 — RSS 뉴스 수집

연합뉴스 · YTN · MBC · SBS · 한국경제 등 공신력 있는 매체의 RSS 피드를 수집해
카테고리별로 정리합니다.

- **수집 매체**: 연합뉴스, YTN, MBC, SBS, 한국경제, 전자신문, 헤럴드경제
- **카테고리**: 하이라이트 · AI · 기술IT · 경제금융 · 사건사고 · 사회 · 자동차 · BMW
- **출력**: `YYYY-MM-DD.md` + `YYYY-MM-DD_data.json`

→ [자세히 보기](./뉴스레터/README.md)

---

## 🌐 GitHub Pages 대시보드

**[siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)**

| 탭 | 내용 |
|----|------|
| 뉴스레터 | 에디터픽 · 카드뉴스 · 수집 뉴스 (카테고리 필터) |
| 코인 트레이더 | 매매 통계 · 누적 손익 차트 · 봇 상태 · 매매 이력 |
| 음악 | 갤럭시 3D 뮤직 유니버스 (Three.js, 7장르 70곡, YouTube 인앱 재생) |
| 소개 | 프로젝트 소개 & AI 크루 |

---

## 🛠 공통 기술 스택

| 구분 | 기술 |
|------|------|
| AI | Gemini 2.5-flash (키 2개) + Groq Llama 3.3 70B (키 4개) — 용도별 우선순위 |
| 이미지 생성 | Pollinations.ai (Flux) |
| 뉴스 수집 | feedparser (RSS) |
| 코인 API | pybithumb (빗썸) |
| 음악 데이터 | YouTube Data API v3 · video_cache.json (119곡 캐시) |
| 유튜브 플레이리스트 | "AI 추천 플레이리스트" 고정, 신곡만 누적 추가 (playlist_state.json) |
| 자동화 | macOS launchd |
| 알림 | ntfy |
| 호스팅 | GitHub Pages |
| 비용 | **$0 (전부 무료)** |

---

## ⚙️ 자동화 구조

```
MacBook (항상 켜짐, pmset -c sleep 0)
│
├── 06:40  launchd → 뉴스레터/newsletter_naver.py      (RSS 뉴스 수집)
├── 07:00  launchd → ai-crew/run_daily.sh              (AI 뉴스레터 생성 + 게시)
│          07:15~20  GitHub Pages 자동 배포 완료
├── 08:30  launchd → coin-trader/main.py report        (일일 리포트)
├── 매 :00/:30 launchd → coin-trader/main.py          (코인 매매 실행, 30분마다)
└── 상시    launchd → coin-trader/price_guard.py       (30초 손절/익절/트레일링 감시)
```

---

*최종 업데이트: 2026-04-23*
