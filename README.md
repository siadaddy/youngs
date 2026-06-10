# youngs

> 평범한 직장인이 Claude를 만나 만든 AI 자동화 모음 — 서버 없이, 비용 없이, 맥북 꺼져도 돌아갑니다.

**라이브 사이트**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)

---

## 📦 프로젝트 목록

| 프로젝트 | 설명 | 실행 주기 |
|---------|------|---------|
| 📰 뉴스 수집 | 네이버 API → 8개 카테고리 + Supabase 저장 | 매일 06:40 KST |
| 🤖 AI 크리에이터 | 카드뉴스 5개 + 이미지 5장 + 음악 큐레이션 → GitHub Pages | 매일 06:40 KST (뉴스 수집 완료 후) |
| 📊 AI 주간 트렌드 | Supabase 7일치 집계 → 분야별 인사이트 브리핑 | 매주 월요일 |
| 🏢 AI 사무실 | 6개 Tron 모니터 + 레이더 패널 — 에이전트 실시간 현황 | 실시간 |
| 🎵 뮤직 유니버스 | AI 큐레이션 270곡 은하계 + MediaPipe 손 인식 컨트롤 | 상시 |
| 🪙 AI 코인봇 | 빗썸 AI 자동매매 — **⛔ 운용 종료 (2026-05-25)** | — |
| 🎓 내 제작물 | 저가 커피 입점 분석 + Instacart 대시보드 | 상시 배포 |

---

## ⚙️ GitHub Actions 자동화 흐름

```
매일 06:40 KST
│
└─ newsletter job
     네이버 API → 8개 카테고리 × 7개 뉴스 수집 (최대 56건)
     → Supabase news_cards / news_trends 저장
     → YYYY-MM-DD.md + _data.json 생성 & 커밋
     → 실패 시 ntfy.sh 즉시 알림
          │
          └─ aicrew job  (newsletter 완료 후 자동 시작)
               최신 커밋 checkout (오늘 .md 포함)
               ├─ [1] 📋 박기획  — 뉴스 5개 선정 + source_facts 추출
               ├─ [2] ✍️  이작가  — 카드뉴스 5개 + 블로그 아티클 (5단계 품질 검수)
               ├─ [3] 🎨 최디자  — HuggingFace FLUX 이미지 5장 → PIL 카드 폴백
               ├─ [4] 🎵 한뮤직  — 7장르 × 10곡 큐레이션 (90일/분기 1회)
               └─ [5] 📊 AI주간트렌드 — Supabase 7일치 인사이트 (월요일만)
               → content.json / archive.json / images/ / office_memory.json 커밋 & push
               → GitHub Pages 자동 반영
               → 실패 시 ntfy.sh 즉시 알림
```

**단일 워크플로우** `.github/workflows/newsletter.yml` 로 전체 파이프라인 통합  
로컬 push 전 반드시 `git pull --rebase origin main` 먼저 실행 (Actions와 동시 push 충돌 방지)

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
│       ├── agent_memory.py   ← AI 직원 자기학습 엔진 (Supabase 동기화)
│       └── office_export.py  ← office_memory.json 생성
│
├── docs/                     ← GitHub Pages 루트
│   ├── index.html            ← 메인 대시보드
│   ├── content.json          ← 오늘 최신 콘텐츠
│   ├── archive.json          ← 날짜별 아카이브 (최대 60일)
│   ├── music.json            ← AI 큐레이션 270곡 (7장르)
│   ├── trades.json           ← 코인봇 매매 이력 (종료 상태 보존)
│   ├── weekly_trend.json     ← 주간 트렌드 브리핑
│   ├── office_memory.json    ← AI 직원 학습 기록 (에이전트별 성장 데이터)
│   ├── content/              ← 날짜별 카드뉴스 JSON (YYYY-MM-DD.json)
│   └── images/               ← AI 생성 이미지 (30일 자동 정리)
│
└── app.py                    ← Instacart 대시보드 (Streamlit)
```

---

## 👥 AI 직원 소개

### 📋 기획자 — 박기획

**모델**: Gemini 2.5-flash → Groq Llama 3.3 70B 폴백 · temperature 0.65 · JSON 모드

- 오늘 뉴스 중 핵심 5개 선정 (카테고리당 최대 3개, 70% 이상 유사 제목 중복 제거)
- 첫 번째 카드는 반드시 **자동차/BMW/전기차** 관련
- 삼천리 그룹 사업전략·실적 뉴스는 5장 중 하나에 강제 포함
- 각 뉴스의 각도(angle), 톤, 키워드, **원문 확인 사실(source_facts)** 기획
- 필터링: 범죄, 연예인 사생활, 정치 편향, 미확인 루머 자동 제외

---

### ✍️ 작가 — 이작가

**모델**: Gemini 2.5-flash → Groq Llama 3.3 70B 폴백 · temperature 0.7 (블로그 0.88)  
**페르소나**: 40대 BMW 딜러 직원 '시아아빠' — 매일 아침 뉴스 읽고 느낀 점 기록

- 카드뉴스 글 5개 (350~450자 + 해시태그 8개)
- 블로그 아티클 1개 (700~900자, 대화체 소제목 2개)
- **source_facts 기반 작성** — 원문에 없는 수치·이름·날짜 창작 금지
- 품질 5단계 후처리: 블랙리스트 → 제목-본문 불일치 → 문장 품질 → 해시태그 위치 교정 → 해시태그 수 검증

---

### 🎨 디자이너 — 최디자

**모델**: Gemini (프롬프트 생성) + **HuggingFace FLUX.1-schnell** (이미지 생성) → PIL 카드 폴백

- 5개 헤드라인용 영문 프롬프트 일괄 생성
- HuggingFace Inference API로 **768×768 이미지 5장** 생성 (최대 3회 재시도)
- 생성 실패 시 PIL로 텍스트 카드 자동 생성 — 사이트 공백 노출 없음
- `docs/images/{날짜}_image_{n}.png` 저장 → GitHub Pages 서빙

---

### 🎵 음악 큐레이터 — 한뮤직

**모델**: Gemini 2.5-flash → Groq 폴백 · temperature 0.85 · JSON 모드  
**수집 주기**: **분기 1회** (90일 미만이면 자동 스킵)

| 장르 | 설명 |
|------|------|
| 2000s힙합 | 2000~2009 미국/영국 힙합 명곡 10곡 |
| 최신힙합 | 2020년 이후 해외 힙합 10곡 |
| 러닝업템포 | BPM 140~180 운동·러닝용 10곡 |
| K-pop | 최근 3년 남자 아이돌/솔로 10곡 |
| 여성발라드 | 한국/팝 여성 보컬 발라드 10곡 |
| 걸그룹 | 최근 3년 K-pop 걸그룹 10곡 |
| 최신곡 | 2024~2025 해외 팝·R&B 10곡 |

- 장르별 개별 호출 (10곡씩 7회) → JSON 잘림 방지
- 손상된 JSON 자동 복구 (`_extract_songs()`) — 잘린 JSON도 유효한 곡만 추출
- 실패 시 전날 music.json 유지 (파이프라인 영향 없음)

---

### 📊 AI주간트렌드

매주 월요일 Supabase `news_trends`에서 7일치 데이터를 집계해 자동 생성.

- TOP3 카테고리 등장 횟수 바 차트 + 분야별 핵심 이슈
- 이번 주를 관통하는 큰 흐름 (투자자·직장인 관점)
- 다음 주 주목할 이슈 3~4개 자동 예측

---

### 🤖 AI 자기학습 시스템

모든 에이전트는 업무 완료 후 회고 → `Supabase agent_memories` 저장

| 컬럼 | 내용 |
|------|------|
| `agent_name` | 에이전트 식별자 (PK) |
| `events` | 업무 이력 JSONB (topic_selection, image_result 등) |
| `diary` | 성장 일기 JSONB |
| `persona` | 자동 진화되는 페르소나 텍스트 |
| `growth_score` | 성장 점수 (5건 일기 누적 시 페르소나 자동 진화) |

GitHub Actions 환경(로컬 `agent_memory.json` 없음) → `_load_from_supabase()`로 자동 복구

---

## 📰 뉴스 수집 상세

- 네이버 뉴스 API — 8개 카테고리 × 최대 7개 = **최대 56건**
- 카테고리: 🔥 하이라이트 / 🤖 AI·인공지능 / 💻 기술·IT / 💰 경제·금융 / 🚨 사건·사고 / 🏙️ 사회 / 🚗 자동차 / 🚘 BMW
- Supabase `news_cards` 원문 저장 + `news_trends` TOP3·요약·이야깃거리 저장
- **오늘의 이야깃거리(talking_points)**: TOP3 트렌드와 별도 풀에서 생성 — 가벼운 생활·스포츠 화제 우선, 동료·임원과 나눌 대화 소재 3개

---

## 🌐 GitHub Pages 대시보드

**라이브**: https://siadaddy.github.io/youngs/

### 주요 섹션

| 섹션 | 내용 |
|------|------|
| 트렌드 브리핑 | 오늘 뉴스 TOP3 카테고리 + 분야별 요약 |
| 이야깃거리 | 동료·임원과 나눌 비즈니스 대화 소재 3개 |
| 키워드 Top 10 | 오늘 뉴스에서 추출한 핵심 단어 바 차트 |
| 카드뉴스 | AI 생성 카드뉴스 5개 + 이미지 |
| 리포트 센터 | AI 주간 트렌드 + **60일 아카이브** (월별 날짜 타일) + **월간 통계** (연속 발행 스트릭, 바 차트) |
| AI 사무실 | Tron 사이버펑크 Canvas — 6개 에이전트 모니터 + 레이더 패널 실시간 인터랙션 |
| 코인 트레이더 | 매매 이력 + 수익률 대시보드 (종료 상태 보존) |

### AI 사무실 상세

Canvas 기반 사이버펑크 다크 오피스. 항상 Tron 모드로 동작합니다.

```
┌──────────────┬─────────────────────────────┬──────────────┐
│   📋 박기획   │       📡 AI CREW HQ          │  📰 뉴스기자  │
│ CONTENT      │   (레이더 + 에이전트 현황)       │ NEWS        │
│ PLANNER      │   5개 블립 + 회전 스윕선        │ COLLECTOR   │
│              │   실시간 시계 + 파이프라인 상태   │             │
├──────────────┴─────────────────────────────┴──────────────┤
│   🎨 최디자  │      📊 AI주간트렌드             │  🎵 한뮤직   │
│ IMAGE        │   TREND ANALYST               │ MUSIC       │
│ DESIGNER     │                               │ CURATOR     │
└──────────────┴────────────────────────────── ┴─────────────┘
[ DATE · · · NEWS · · · · · · · · · · · CREW · · · · TOP ]  ← 인포바
```

- 6개 에이전트 모니터 + 중앙 레이더 패널(시스템 상태 HQ)
- 레이더: 회전 스윕선, 5개 에이전트 블립(스캔 시 펄스), 실시간 초 단위 시계
- 하단 인포바: 날짜 · 오늘의 뉴스 · 에이전트 현황 · 키워드 Top
- Tron 원근 그리드 배경 (네온 사이버펑크)

---

## 🎵 뮤직 유니버스

AI가 큐레이션한 270곡이 은하계를 이루고, 별 하나가 한 곡입니다.

**라이브**: [siadaddy.github.io/youngs/music.html](https://siadaddy.github.io/youngs/music.html)

### YouTube Music 자동 플레이리스트

| 구분 | 내용 |
|------|------|
| 전체 누적 플레이리스트 | 270곡 (고정 ID, 날마다 신곡만 추가) |
| 장르별 플레이리스트 | 18개 장르로 자동 분류 (235곡 자동 매핑) |
| video_cache.json | 곡명→videoId 캐시 (306곡) |
| 쿼터 | YouTube Data API 일 10,000 units (KST 09:00 리셋) |

### 손 인식 컨트롤 (MediaPipe Hands)

| 제스처 | 동작 |
|--------|------|
| ☝️ 검지 이동 | 글로우 커서 이동 + 별 호버 |
| 🤏 엄지+검지 꽉 모음 | 클릭 → 유튜브 재생 |
| 👌 엄지+검지 벌리기/모으기 | 줌인 / 줌아웃 |
| ✊ 주먹 쥐고 이동 | 은하 드래그 회전 |
| 🖐 손 펴고 스와이프 | 이전 / 다음 곡 |

- 별도 설치 없이 브라우저에서 바로 실행 (HTTPS 환경)
- Three.js + UnrealBloom 후처리 + OrbitControls

---

## 🪙 AI 코인봇 (⛔ 운용 종료)

| 항목 | 값 |
|------|-----|
| 운용 기간 | 2026-03 ~ 2026-05-25 |
| 총 거래 | 103회 |
| 최종 승률 | 33% |
| 누적 손익 | **-46,877원** |

빗썸 KRW 마켓 AI 트레이딩. launchd 등록 해제됨. 코드 및 매매 이력은 참조용으로 보존.

**매매 로직**: 24h 거래대금 20억↑ 종목 → RSI·MACD·볼린저밴드·ADX·변동성돌파 스코어링 → Groq AI 판단 → 빗썸 시장가 주문

**안전장치**: 손절 -4% / 익절 +5% / 트레일링스탑(+3% 활성) / 강제청산(8h 보유 -1% 이하) / 일일 드로우다운 -7,500원 정지 / 학습 블랙리스트

---

## 🛠 기술 스택

| 기술 | 용도 | 비용 |
|------|------|------|
| 네이버 뉴스 API | 뉴스 수집 (8개 카테고리) | 무료 |
| Supabase | 뉴스 원문·트렌드·에이전트 메모리 DB | 무료 |
| Gemini 2.5 Flash | 텍스트 생성 (우선) | 무료 |
| Groq Llama 3.3 70B | 텍스트 생성 (폴백, 키 4개 라운드로빈) | 무료 |
| HuggingFace FLUX.1-schnell | AI 이미지 768×768 | 무료 |
| PIL (Pillow) | 이미지 생성 폴백 (카드 텍스트) | 무료 |
| YouTube Data API v3 | 음악 검색 + IFrame 재생 | 무료 |
| Three.js (WebGL) | 갤럭시 3D 뮤직 유니버스 | 무료 |
| MediaPipe Hands | 웹캠 손 제스처 인식 | 무료 |
| GitHub Pages | 콘텐츠 호스팅 | 무료 |
| GitHub Actions | 전체 파이프라인 자동화 | 무료 |
| ntfy.sh | 완료·실패 즉시 알림 | 무료 |
| **합계** | | **$0** |

---

## 🛡 콘텐츠 품질 보호

| 레이어 | 내용 |
|--------|------|
| 뉴스 수집 | 70% 이상 유사 제목 자동 중복 제거 |
| 기획자 필터 | 범죄, 연예인 사생활, 정치 편향, 미확인 루머 자동 제외 |
| source_facts | 원문 확인 사실만 추출 → 작가가 이것만 사용하도록 강제 |
| 작가 5단계 후처리 | 블랙리스트 → 제목-본문 불일치 → 문장 품질 → 해시태그 위치 → 해시태그 수 |
| 언어 필터 | 일본어·아랍어·태국어·러시아어·힌디어 자동 제거 |
| 키워드 스탑워드 | 언론사명·포괄어·조사형·시간표현 등 45개 이상 필터링 |
| 이미지 폴백 | HuggingFace 실패 시 PIL 카드 자동 생성 — 공백 노출 없음 |

---

## 🎓 내 제작물

### ☕ 저가 테이크아웃 커피 브랜드 입점 최적지 분석
서울 유동인구·상권·임대료 데이터로 메가커피·컴포즈 최적 입점 후보지 도출 + Folium 지도 시각화

**라이브**: [siadaddy.github.io/youngs/map.html](https://siadaddy.github.io/youngs/map.html)

### 🛒 Instacart VIP 분석 대시보드
인스타카트 구매 데이터로 VIP 고객 분류 + 맞춤 상품 추천 인터랙티브 대시보드

**배포**: [youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app](https://youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app)

---

## 📅 업데이트 로그

### 2026-06
- **AI 사무실 전면 개편**: 픽셀아트 → Tron 사이버펑크 Canvas, 6개 에이전트 모니터 + 레이더 패널(AI CREW HQ)
- **리포트 센터 신설**: AI 주간 트렌드 탭 → 60일 아카이브 + 월간 통계(스트릭·바 차트) 통합
- **장르별 YouTube 플레이리스트**: 270곡 → 18개 장르 자동 분류
- **오늘의 이야깃거리**: TOP3 트렌드와 별도 풀 생성, 생활·스포츠 화제 우선
- **GitHub Actions 실패 알림**: newsletter·aicrew job 실패 시 ntfy.sh 즉시 푸시
- **키워드 스탑워드 대폭 확장**: 14일치 실데이터 분석 기반 45개 이상 필터 추가
- **Supabase agent_memories**: 단일 data 컬럼 → 컬럼 분리 (events/diary/persona/growth_score)

### 2026-05
- **코인봇 운용 종료** (2026-05-25): 103회 거래, 승률 33%, 손익 -46,877원
- **GitHub Actions 완전 이전**: launchd → newsletter.yml 단일 워크플로우
- **이미지 생성 전환**: Pollinations.ai → HuggingFace FLUX.1-schnell + PIL 폴백
- **모바일 640px 최적화**: index.html 레이아웃 전면 개선

### 2026-04
- **AI 직원 자기학습 시스템**: agent_memory.py + Supabase 동기화 + 페르소나 진화
- **음악 큐레이터**: 7장르×10곡, 분기 1회 수집, YouTube 누적 플레이리스트
- **뮤직 유니버스**: Three.js 은하계 + MediaPipe 손 인식 컨트롤

### 2026-03
- 시스템 최초 구축

---

*최종 업데이트: 2026-06-10 | Powered by Gemini · Groq · Supabase · HuggingFace · MediaPipe · GitHub Actions · GitHub Pages | 월 운영비용 $0*
