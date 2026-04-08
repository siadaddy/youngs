# 🤖 시아아빠님의 AI 자동화 허브

> **매일 아침**, AI 직원들이 뉴스를 읽고 콘텐츠를 만들고, 음악을 큐레이션하고, 코인을 삽니다.

🌐 **라이브 사이트**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)

---

## 📋 시스템 개요

네이버 뉴스를 수집해 AI 에이전트 5명이 협업하여 카드뉴스 · 블로그 · 이미지를 자동 생성하고 GitHub Pages에 배포합니다.
Groq AI가 매일 인기 음악 70곡+를 큐레이션해 3D 우주 공간에 뿌려놓고, AI 코인 트레이더가 실시간으로 시장을 감시합니다.

**실행 환경**: MacBook (launchd) — 서버 불필요, 완전 로컬 자동화 | **월 운영 비용: $0**

---

## 🗂 3탭 서비스 구성

| 탭 | 기능 | 업데이트 주기 |
|----|------|--------------|
| 📰 AI 뉴스레터 | 카드뉴스 5개 + 블로그 아티클 + 이미지 5장 | 매일 07:00 |
| 🤖 코인 트레이더 | AI 실시간 매매 현황 + 히스토리 | 30초 갱신 |
| 🌌 뮤직 유니버스 | AI 큐레이션 70곡+ 3D 우주 + YouTube 재생 | 매일 07:00 |

---

## 🕐 자동화 스케줄

```
07:00 KST  🤖 run_daily.sh 실행 (launchd)
           │
           ├─ Step 1: 뉴스레터 수집 (newsletter_naver.py)
           │    네이버 뉴스 API → 8개 카테고리 수집
           │    Groq AI → 카테고리별 요약 + TOP 3 선정
           │    → .md / _data.json 로컬 저장
           │
           └─ Step 2: AI 크리에이터 (main.py)
                [1/5] 뉴스레터 로드
                [2/5] 기획자 → 콘텐츠 브리프 생성
                [3/5] 작가  → 카드뉴스 5개 + 블로그 아티클
                [4/5] 디자이너 → 이미지 5장 → docs/images/
                [5/5] 음악 큐레이터 → 70곡+ → docs/music.json
                → GitHub Pages 자동 push
                → ntfy 완료 알림

~08:00 KST  ✅ 완료 | 📱 ntfy 알림 수신
```

---

## 👥 AI 직원 소개

### 🎯 기획자 — 박기획
**역할**: 뉴스레터 분석 → 카드뉴스 5개 + 블로그 주제 기획
**모델**: Groq Llama 3.3 70B
- 핵심 뉴스 5개 선정 (1번은 반드시 자동차/BMW/전기차)
- 각 뉴스의 각도·톤·source_facts(원문 400자) 추출
- 범죄·정치편향·자극적 뉴스 자동 필터링

### ✍️ 작가 — 시아아빠
**역할**: 기획 브리프 → 카드뉴스 글 5개 + 블로그 아티클 작성
**모델**: Groq Llama 3.3 70B (temperature 0.7 / 블로그 0.88)
**페르소나**: 40대 BMW 딜러 직원, 친구한테 카톡 보내듯 편하게 쓰되 내용은 진짜 있게
- 카드뉴스 350~450자 + 해시태그 8개
- 블로그 700~900자, 대화체 소제목 2개
- source_facts 기반 — 없는 수치·이름 창작 금지

### 🎨 디자이너 — 최디자
**역할**: 헤드라인 → AI 이미지 프롬프트 → 이미지 5장 생성
**모델**: Groq Llama 3.3 70B (프롬프트) + Pollinations.ai Flux (이미지, 키 불필요)
- 768×768 SNS 카드뉴스 스타일 (Bloomberg/Wired 톤)
- `docs/images/{날짜}_image_{n}.png` 저장

### 🎵 음악 큐레이터 — 뮤직AI
**역할**: 매일 전 세계 인기 음악 70곡+ 큐레이션 → music.json 저장
**모델**: Groq Llama 3.3 70B (temperature 0.85)
- K-pop 30곡 / 한국 인디·팝·R&B·힙합 15곡 / 팝 20곡 / R&B·힙합·일렉트로팝 10곡
- 트롯·클래식·동요 제외, 최근 2~3년 내 발매 위주
- 한 아티스트 최대 3곡 | 중복 자동 제거

### 📤 노션 퍼블리셔 — 정퍼블
**역할**: 결과물 → 노션 페이지 통합 업로드
- 카드뉴스 5개(이미지+글) + AI 에디터 PICK + 수집 뉴스 목록
- 2000자 초과 텍스트 자동 분할

### 📅 주간 브리퍼 — 한주간
**역할**: 매주 금요일, 이번 주 뉴스 5일치 → 주간 종합 브리핑
**모델**: Groq Llama 3.3 70B (temperature 0.65)

---

## 🌌 뮤직 유니버스

- **Three.js WebGL 3D** 은하 공간에 AI 큐레이션 노래들이 별로 떠다님
- 접속할 때마다 **완전히 다른 3D 배치** (구형 랜덤 분포)
- **배경**: 다층 별 필드(12,000개+) · 은하수 띠 · 성운 7개 · 지구 · 별똥별
- **재생**: 별 클릭 → YouTube Data API 검색 → 인앱 IFrame 플레이어 재생
- **뮤직 리액티브**: 재생 시 bloom 강화 · 회전 가속 · 별 맥동 (~120BPM 시뮬레이션)
- **방향 전환**: ~3분 주기 자동 방향 반전 + 다축 틸트로 3D 입체감
- **YouTube API**: HTTP Referrer 제한 (`siadaddy.github.io/*`) 적용

---

## 🗂 파일 구조

```
docs/                           ← GitHub Pages 루트
├── index.html                  ← 메인 (3탭: 뉴스레터·코인·뮤직)
├── music.html                  ← Music Universe 3D 페이지
├── music.json                  ← AI 큐레이션 노래 목록 (매일 갱신)
├── content.json                ← 오늘 최신 콘텐츠
├── archive.json                ← 날짜 목록 (최대 60일)
├── trades.json                 ← 코인 트레이더 거래 내역
├── content/
│   └── YYYY-MM-DD.json         ← 날짜별 콘텐츠 아카이브
├── images/
│   └── YYYY-MM-DD_image_N.png  ← AI 생성 이미지
├── about.html                  ← AI 직원 소개 페이지
├── map.html                    ← 커피 입지 분석 지도
└── SA대시보드_demo.html         ← BMW SA 성과 대시보드

바이브코딩/
├── 뉴스레터/
│   ├── newsletter_naver.py     ← 뉴스 수집 + Groq 요약
│   ├── .env                    ← NAVER + GROQ 키 (git 미추적)
│   ├── YYYY-MM-DD.md           ← 날짜별 뉴스레터 백업
│   └── YYYY-MM-DD_data.json    ← AI 크리에이터용 구조화 데이터
│
├── ai-crew/
│   ├── main.py                 ← 오케스트레이터 (5단계, 각 3회 재시도)
│   ├── run_daily.sh            ← launchd 실행 스크립트
│   ├── agents/
│   │   ├── planner.py          ← 🎯 기획자
│   │   ├── writer.py           ← ✍️  작가
│   │   ├── designer.py         ← 🎨 디자이너
│   │   ├── music_curator.py    ← 🎵 음악 큐레이터 (NEW)
│   │   ├── notion_publisher.py ← 📤 노션 퍼블리셔
│   │   └── weekly_briefer.py   ← 📅 주간 브리퍼
│   ├── utils/
│   │   ├── gemini_client.py    ← Groq API 클라이언트 (key1→key2 폴백)
│   │   └── notion_reader.py    ← 로컬 .md 파일 읽기
│   └── .env                    ← GROQ + NOTION + NTFY 키 (git 미추적)
│
└── coin-trader/
    ├── main.py                 ← AI 코인 자동매매
    └── .env                    ← 업비트 API 키 (git 미추적)
```

---

## 🔧 .env 설정

### `바이브코딩/뉴스레터/.env`
```
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
GROQ_API_KEY=...
GROQ_API_KEY_2=...
```

### `바이브코딩/ai-crew/.env`
```
GROQ_API_KEY=...
GROQ_API_KEY_2=...
NOTION_TOKEN=...
NOTION_NEWSLETTER_PARENT_ID=...
NEWSLETTER_DIR=/Users/youngchulyu/바이브코딩/뉴스레터
NTFY_TOPIC=siadad-aicrew
```

---

## 🛠 사용 기술 & 비용

| 기술 | 용도 | 비용 |
|------|------|------|
| Naver News API | 뉴스 수집 (8개 카테고리) | 무료 |
| Groq (Llama 3.3 70B) | 텍스트 생성 전반 · 음악 큐레이션 | 무료 |
| Pollinations.ai (Flux) | AI 이미지 생성 768×768 | 무료 |
| YouTube Data API v3 | 음악 검색 + IFrame 재생 | 무료 |
| Three.js (WebGL) | 3D 뮤직 유니버스 | 무료 |
| GitHub Pages | 콘텐츠 호스팅 + 3탭 사이트 | 무료 |
| ntfy.sh | 완료 알림 | 무료 |
| **합계** | | **$0** |

---

## 🔐 보안

| 항목 | 상태 |
|------|------|
| `.env` 파일 | git 미추적 ✅ |
| Groq API 키 | 환경변수만 사용, 코드에 미노출 ✅ |
| Notion 토큰 | 환경변수만 사용, 코드에 미노출 ✅ |
| 업비트 API 키 | 환경변수만 사용, 코드에 미노출 ✅ |
| YouTube Data API 키 | 프론트엔드 사용 (불가피) — HTTP Referrer 제한 적용 (`siadaddy.github.io/*`) ⚠️→✅ |

---

## 🔄 자동 재시도 구조

| 단계 | 실패 시 동작 |
|------|-------------|
| 뉴스레터 로드 | 3회 재시도 → 모두 실패 시 종료 + ntfy 알림 |
| 기획자 | 3회 재시도 → 모두 실패 시 종료 + ntfy 알림 |
| 작가 | 3회 재시도 → 모두 실패 시 종료 + ntfy 알림 |
| 디자이너 | 3회 재시도 → 실패해도 빈 이미지로 계속 진행 |
| 음악 큐레이터 | 3회 재시도 → 실패해도 무시 (전날 music.json 유지) |
| Groq 429 | retry-after 대기 → key2 자동 전환 |

재시도 간격: **10초**

---

## 🚀 수동 실행

```bash
# 전체 파이프라인
/Users/youngchulyu/바이브코딩/ai-crew/run_daily.sh

# 음악 큐레이터만
cd /Users/youngchulyu/바이브코딩/ai-crew
python3 -m agents.music_curator

# 로그 확인
tail -f /Users/youngchulyu/바이브코딩/ai-crew/crew.log
```

---

## 📝 업데이트 로그

### 2026-04-09
- **뮤직 유니버스 완성**: 제작물 카드 → 🌌 뮤직 유니버스 탭으로 승격 (iframe 레이지 로드)
- **3D 배경 우주화**: 다층 별 12,000개 · 은하수 띠 · 성운 7개 · 지구(자전·구름·대기권) · 별똥별
- **노드 배치 3D화**: 4팔 나선 → 구형 랜덤 배치 (접속마다 다른 우주)
- **회전 다방향화**: 사인파 방향 전환 (~3분 주기) + 다축 틸트 (galaxyGroup X/Z 축)
- **브랜딩**: NOW PLAYING 토스트 · 로고 서브타이틀 · 힌트 문구 감성화

### 2026-04-08
- **🎵 음악 큐레이터 에이전트 신규 추가** (`agents/music_curator.py`)
  - Groq Llama 3.3 70B로 매일 70곡+ 큐레이션 → `docs/music.json`
  - main.py Step 5로 편입, 실패해도 파이프라인 계속 진행
- **뮤직 유니버스 신규** (`docs/music.html`)
  - Three.js WebGL 3D 은하 · OrbitControls · UnrealBloomPass
  - YouTube Data API v3 + IFrame Player API 인앱 재생
  - 뮤직 리액티브: 재생 시 bloom·회전·맥동 강화 (~120BPM 비트 시뮬레이션)
  - HTTP Referrer 제한 적용 (`siadaddy.github.io/*`)

### 2026-04-03
- **작가 페르소나**: "수석 저널리스트" → **시아아빠** (40대 BMW 딜러)
- **글쓰기 품질 개선**: 물음표 1개 제한, 금지 문구 강화, 블로그 700~900자

### 2026-04-02
- 이미지 재시도 로직: 429/5xx → 최대 3회 (즉시→20초→40초)

### 2026-04-01
- 이미지 생성: Stable Horde → **Pollinations.ai** 전환 (키 불필요, 안정적)

### 2026-03-28
- **AI 코인 트레이더** 신규 구축 (`바이브코딩/coin-trader/`)
- 코인 트레이더 GitHub Pages 탭 추가

### 2026-03-27
- GitHub Actions → **macOS launchd** 로컬 자동화 전환
- 이미지 호스팅: freeimage.host → **GitHub Pages** `docs/images/`
- Groq 듀얼 키 폴백 구조 도입

### 2026-03-26
- 카드뉴스 3개 → **5개**, 이미지 3장 → **5장**
- GitHub Pages 배포 + 날짜별 아카이브

### 2026-03-25
- 시스템 최초 구축

---

*최종 업데이트: 2026-04-09 | Powered by Groq + Pollinations.ai + YouTube API + Three.js + Notion API + GitHub Pages*
