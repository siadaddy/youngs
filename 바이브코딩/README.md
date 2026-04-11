# 🤖 youngchulyu — AI 자동화 프로젝트 모음

> MacBook 위에서 24시간 돌아가는 AI 자동화 시스템들

**라이브 대시보드**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)

---

## 📦 프로젝트 구성

| 프로젝트 | 설명 | 실행 주기 |
|---------|------|---------|
| [ai-crew](./ai-crew/) | AI 뉴스레터 자동 생성 (에디터픽 + 카드뉴스) | 매일 07:30 |
| [coin-trader](./coin-trader/) | AI 코인 자동매매 (빗썸 KRW 마켓) | 5분마다 |
| [뉴스레터](./뉴스레터/) | RSS 뉴스 자동 수집 & 카테고리 분류 | 매일 07:00 |
| [docs](./docs/) | GitHub Pages 대시보드 | — |

---

## 📰 ai-crew — AI 뉴스레터

RSS로 수집된 뉴스를 바탕으로 Groq AI가 에디터픽 기사와 카드뉴스를 자동 생성합니다.

- **AI 모델**: Groq Llama 3.3 70B
- **이미지**: Pollinations.ai (Flux 모델)
- **품질 검사**: 3단계 (완성도 · 제목-본문 일관성 · 문장 품질)
- **출력**: GitHub Pages 뉴스레터 탭 자동 게시

```
뉴스 수집(RSS) → AI 기사 작성 → 이미지 생성 → GitHub Pages 게시
```

→ [자세히 보기](./ai-crew/README.md)

---

## 🪙 coin-trader — AI 코인 자동매매

빗썸 KRW 마켓 상위 20개 종목을 분석해 Groq AI가 매매를 자동 실행합니다.

- **분석**: 30분봉 RSI · MACD · 볼린저밴드 · ADX · 변동성 돌파
- **안전장치**: 손절 -4% / 익절 +6% / Daily Drawdown -15,000원
- **알림**: ntfy 실시간 푸시 알림
- **대시보드**: 누적 손익 차트 · 봇 상태 · 매매 이력

```
매 5분: 시장 분석 → AI 판단(BUY/SELL/HOLD) → 주문 실행 → 대시보드 업데이트
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
| 음악 | 한국 인기 음악 3D 별자리 비주얼라이저 |
| 소개 | 프로젝트 소개 & AI 크루 |

---

## 🛠 공통 기술 스택

| 구분 | 기술 |
|------|------|
| AI | Groq API (Llama 3.3 70B) |
| 이미지 생성 | Pollinations.ai (Flux) |
| 뉴스 수집 | feedparser (RSS) |
| 코인 API | pybithumb (빗썸) |
| 음악 데이터 | YouTube Data API · iTunes API |
| 자동화 | macOS launchd |
| 알림 | ntfy |
| 호스팅 | GitHub Pages |
| 비용 | **$0 (전부 무료)** |

---

## ⚙️ 자동화 구조

```
MacBook (항상 켜짐, pmset -c sleep 0)
│
├── 07:00  launchd → 뉴스레터/newsletter_rss.py   (RSS 수집)
├── 07:30  launchd → ai-crew/main.py              (AI 뉴스레터 생성 + 게시)
└── 매 5분 launchd → coin-trader/main.py          (코인 매매 실행)
```

---

*최종 업데이트: 2026-04-11*
