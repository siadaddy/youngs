# youngs

> 평범한 직장인이 Claude를 만나 만든 AI 자동화 모음 — 서버 없이, 비용 없이, 맥북 꺼져도 돌아갑니다.

**라이브 사이트**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)

---

## 📦 프로젝트 목록

| 프로젝트 | 설명 | 실행 주기 |
|---------|------|---------|
| 📰 뉴스 수집 | 네이버 API → 8개 카테고리 + Supabase 저장 | 매일 06:40 KST |
| 🤖 AI 크리에이터 | 카드뉴스 5개 + 이미지 5장 + 음악 큐레이션 → GitHub Pages | 매일 07:10 KST |
| 📊 AI 주간 트렌드 | Supabase 7일치 집계 → 분야별 인사이트 브리핑 | 매주 월요일 |
| 🪙 AI 코인 자동매매 | 빗썸 KRW 마켓 AI 트레이딩 + 대시보드 | 30분마다 (맥북) |
| 🏢 AI 사무실 | 8명 AI 직원 픽셀아트 오피스 — 낮/밤 자동 전환 | 실시간 |
| 🎵 뮤직 유니버스 | AI 큐레이션 은하계 + MediaPipe 손 인식 컨트롤 | 상시 |
| 🎓 내 제작물 | 저가 커피 입점 분석 + Instacart 대시보드 | 상시 배포 |

---

## 🗂 저장소 구조

```
youngs/
├── .github/workflows/
│   └── newsletter.yml        ← GitHub Actions (뉴스수집 → AI크리에이터 순차 실행)
│
├── newsletter/
│   ├── newsletter_naver.py   ← 네이버 API 뉴스 수집 + Supabase 저장 + .md 생성
│   └── YYYY-MM-DD.md         ← 날짜별 뉴스레터 백업
│
├── ai-crew/
│   ├── main.py               ← AI 크리에이터 오케스트레이터
│   ├── agents/               ← 박기획·이작가·최디자·한뮤직·AI주간트렌드
│   └── utils/
│       ├── gemini_client.py  ← Gemini 2.5 Flash + Groq 폴백
│       ├── notion_reader.py  ← .md 파일 읽기
│       └── agent_memory.py   ← AI 직원 자기학습 엔진
│
├── docs/                     ← GitHub Pages 루트
│   ├── index.html            ← 메인 대시보드
│   ├── content.json          ← 오늘 최신 콘텐츠
│   ├── archive.json          ← 날짜별 아카이브
│   ├── music.json            ← AI 큐레이션 70곡
│   ├── trades.json           ← 코인 매매 이력
│   ├── weekly_trend.json     ← 주간 트렌드 브리핑
│   ├── office_memory.json    ← AI 직원 학습 기록
│   ├── content/              ← 날짜별 콘텐츠 JSON
│   └── images/               ← AI 생성 이미지
│
└── app.py                    ← Instacart 대시보드 (Streamlit)
```

---

## ⚙️ GitHub Actions 자동화 흐름

```
매일 06:40 KST
│
└─ newsletter job
     네이버 API → 8카테고리 × 7개 뉴스 수집
     → Supabase news_cards / news_trends 저장
     → YYYY-MM-DD.md + _data.json 생성 & 커밋
          │
          └─ aicrew job  (newsletter 완료 후 자동 시작)
               최신 커밋 checkout (오늘 .md 포함)
               ├─ [1] 📋 박기획  — 뉴스 5개 선정
               ├─ [2] ✍️  이작가  — 카드뉴스 5개 + 블로그 아티클
               ├─ [3] 🎨 최디자  — Pollinations.ai 이미지 5장
               ├─ [4] 🎵 한뮤직  — 7장르 × 10곡 큐레이션 (주 1회)
               └─ [5] 📊 AI주간트렌드 — Supabase 7일치 인사이트 (월요일)
               → content.json / archive.json / images/ 커밋 & push
               → GitHub Pages 자동 반영
```

**단일 워크플로우** `.github/workflows/newsletter.yml` 로 전체 파이프라인 통합

---

## 📰 뉴스 수집 + 🤖 AI 크리에이터

### 뉴스 수집 특징
- 네이버 뉴스 API — 8개 카테고리 × 최대 7개 = 최대 **56개** 기사
- 카테고리: 🔥 하이라이트 / 🤖 AI·인공지능 / 💻 기술·IT / 💰 경제·금융 / 🚨 사건·사고 / 🏙️ 사회 / 🚗 자동차 / 🚘 BMW
- **Supabase** `news_cards` 테이블에 원문 저장 → 프론트에서 실시간 조회
- `news_trends` 테이블에 TOP3·카테고리 요약·이야깃거리 저장

### AI 크리에이터 특징
- **source_facts 기반**: 원문에 없는 수치·사실 창작 금지
- **품질 5단계 후처리**: 블랙리스트 → 제목-본문 일관성 → 문장 품질 → 해시태그
- **AI 직원 자기학습**: 업무 완료 후 1문장 회고 → `agent_memory.json` → 성장 점수(Lv.)

### 기술 스택

| 기술 | 용도 | 비용 |
|------|------|------|
| 네이버 뉴스 API | 뉴스 수집 | 무료 |
| Supabase | 뉴스 원문·트렌드 DB | 무료 |
| Gemini 2.5 Flash | 텍스트 생성 (우선) | 무료 |
| Groq Llama 3.3 70B | 텍스트 생성 (폴백) | 무료 |
| Pollinations.ai Flux | AI 이미지 768×768 | 무료 |
| GitHub Pages | 콘텐츠 호스팅 | 무료 |
| GitHub Actions | 전체 파이프라인 자동화 | 무료 |

---

## 📊 GitHub Pages 대시보드 주요 섹션

| 섹션 | 내용 |
|------|------|
| 트렌드 브리핑 | 오늘 뉴스 TOP3 카테고리 + 분야별 요약 |
| 이야깃거리 | 동료·임원과 나눌 비즈니스 대화 소재 3개 |
| 키워드 Top 10 | 오늘 뉴스에서 추출한 핵심 단어 바 차트 |
| 카드뉴스 | AI 생성 카드뉴스 5개 + 이미지 |
| AI 주간 트렌드 | 주간 분야별 인사이트 + 다음 주 주목 이슈 |
| AI 사무실 | 픽셀아트 오피스 실시간 인터랙션 |
| 코인 트레이더 | 매매 이력 + 수익률 대시보드 |

---

## 📊 AI 주간 트렌드

매주 월요일, Supabase `news_trends`에서 7일치 데이터를 집계해 자동 생성합니다.

- **TOP3 카테고리 등장 횟수** 기반 바 차트 (최대 21회)
- **분야별 핵심 이슈 + 인사이트** 상위 4개 분야
- **이번 주를 관통하는 큰 흐름** (투자자·직장인 관점)
- **다음 주 주목할 이슈** 3~4개 자동 예측
- **히스토리**: 최대 12주치 아카이브

---

## 🪙 AI 코인 자동매매

빗썸 KRW 마켓을 분석하고 Groq AI가 매매를 자동 실행합니다. (맥북 로컬 실행)

**라이브 대시보드**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/) → 코인 트레이더 탭

### 매매 흐름

```
매 30분
├─ Daily Drawdown 체크 (한도 초과 시 당일 정지)
├─ 24h 거래대금 20억원 이상 종목 선별
├─ 블랙리스트·스테이블코인 자동 제외
├─ 1시간봉 RSI·MACD·볼린저밴드·ADX·변동성돌파 계산 (병렬 5개)
├─ 스코어링 → Groq AI 매매 판단
├─ 빗썸 시장가 주문 실행
└─ docs/trades.json → GitHub Pages push

상시  🛡️ price_guard.py — 30초마다 손절/익절 즉시 감시
08:30 리포터 — 전날 손익 집계 → 일일 리포트
```

### 스코어링 기준 (매수 최소 +7점)

| 지표 | 조건 | 점수 |
|------|------|------|
| RSI (1시간봉) | 25~35 | +3 |
| RSI | 35~45 | +2 |
| MACD | 골든크로스 (필수) | +3 |
| 변동성 돌파 + 거래량 50%↑ | VB + vol | +4 |
| ADX | ≥40 | +2 |
| ADX | ≥35 | +1 |

### 안전장치

| 기능 | 기준 |
|------|------|
| 손절 | -4% |
| 익절 | +5% |
| 트레일링스탑 | +3% 활성 → 고점 대비 -2.5% |
| 강제청산 | 8시간 보유 + 수익률 -1% 이하 |
| 학습 블랙리스트 | 손절 2회→3일 / 3회→7일 / 4회→14일 / 5회→30일 |
| Daily Drawdown | -7,500원 초과 시 당일 정지 |
| 투자금 | 5만원 (실거래 중) |

---

## 🏢 AI 사무실

Canvas 픽셀아트 인터랙티브 오피스. 8명의 AI 직원이 실데이터를 말풍선으로 표시합니다.

- **낮/밤 자동 전환**: 07~19시 ☀️ 원목 오피스 / 19~07시 🌙 사이버펑크 다크
- **19가지 행동 패턴**: 걷기·커피·스트레칭·통화·춤·회의 등
- **말풍선**: `office_memory.json` 실데이터 반영 (승률, 최근 매매, 성장 기록)
- **2~3분마다 전체 회의**: 일일 브리핑 자동 진행

---

## 🎵 뮤직 유니버스

AI가 큐레이션한 70곡이 은하계를 이루고, 별 하나가 한 곡입니다.

**라이브**: [siadaddy.github.io/youngs/music.html](https://siadaddy.github.io/youngs/music.html)

### ✋ 손 인식 컨트롤 (MediaPipe Hands)

카메라를 켜고 손 제스처만으로 우주를 탐색할 수 있습니다.

| 제스처 | 동작 |
|--------|------|
| ☝️ 검지 이동 | 글로우 커서 이동 + 별 호버 |
| 🤏 엄지+검지 **꽉 모음** | 클릭 → 유튜브 재생 |
| 👌 엄지+검지 **벌리기/모으기** | 줌인 / 줌아웃 |
| ✊ 주먹 쥐고 이동 | 은하 드래그 회전 |
| 🖐 손 펴고 스와이프 | 이전 / 다음 곡 |
| 🤲 양손 벌리기/모으기 | 빠른 줌인 / 줌아웃 |

- 별도 설치 없이 브라우저에서 바로 실행 (HTTPS 환경)
- Three.js + UnrealBloom 후처리 + OrbitControls

---

## 🎓 내 제작물

### ☕ 저가 테이크아웃 커피 브랜드 입점 최적지 분석
서울 유동인구·상권·임대료 데이터로 메가커피·컴포즈 최적 입점 후보지 도출 + Folium 지도 시각화

**라이브**: [siadaddy.github.io/youngs/map.html](https://siadaddy.github.io/youngs/map.html)

### 🛒 Instacart VIP 분석 대시보드
인스타카트 구매 데이터로 VIP 고객 분류 + 맞춤 상품 추천 인터랙티브 대시보드

**배포**: [youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app](https://youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app)

---

*최종 업데이트: 2026-05-12 | Powered by Gemini · Groq · Supabase · Pollinations.ai · MediaPipe · pybithumb · GitHub Actions · GitHub Pages | 월 운영비용 $0*
