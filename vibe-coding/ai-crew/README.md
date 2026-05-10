# 🤖 시아아빠님의 AI 크리에이터

> 매일 아침, AI 직원들이 뉴스를 읽고 콘텐츠를 만들어 GitHub Pages에 자동 배포합니다.

**라이브 사이트**: https://siadaddy.github.io/youngs/

---

## 📋 시스템 개요

RSS 피드로 수집한 뉴스를 바탕으로, 역할이 다른 AI 에이전트들이 협업해
카드뉴스 5개 + 블로그 아티클 + 이미지 5장 + 오늘의 음악 70곡을 자동 생성하고 GitHub Pages에 배포합니다.

**실행 환경**: MacBook (launchd) — 서버 불필요, 완전 로컬 자동화

---

## 🕐 자동화 스케줄

```
06:40 KST  📰 뉴스 수집 (com.siadad.newsletter LaunchAgent)
               newsletter_naver.py 실행
               RSS 8개 카테고리 수집 (연합뉴스·YTN·MBC·SBS·한경·전자신문·헤럴드)
               → YYYY-MM-DD.md / YYYY-MM-DD_data.json 저장

07:00 KST  🤖 run_daily.sh 실행 (com.siadad.aicrew LaunchAgent)
           │
           ├─ 뉴스 데이터 파일 존재 확인
           │    없으면 긴급 수집 폴백 실행 후 진행
           │
           └─ AI 크리에이터 (main.py)
                기획자 → 작가 → 디자이너 → 음악 큐레이터* → GitHub 배포
                → docs/images/ 저장 → GitHub Pages 자동 push
                각 단계 실패 시 최대 3회 자동 재시도

~07:20 KST  ✅ 모든 작업 완료
             📱 ntfy 앱으로 완료 알림 수신

* 음악 큐레이터: 마지막 수집이 7일 미만이면 자동 스킵 (주 1회만 실행)
```

**절전 대응**: `sudo pmset repeat wakeorpoweron MTWRFSU 06:35:00` 으로 맥북 자동 깨움

---

## 👥 AI 직원 소개

### 🎯 기획자 — 박기획

> "오늘 어떤 뉴스가 사람들 마음을 움직일까요?"

**모델**: Gemini 2.5-flash → Groq Llama 3.3 70B 폴백 · temperature 0.65 · JSON 모드
**담당**:
- 오늘 뉴스 중 핵심 뉴스 **5개** 선정 (카테고리당 최대 3개, 70% 이상 유사 제목 중복 제거)
- 첫 번째 카드는 반드시 **자동차/BMW/전기차** 관련
- 각 뉴스의 각도(angle), 톤, 키워드, **원문 확인 사실(source_facts)** 기획
- 블로그 아티클 주제 1개 선정 (임팩트 큰 국제/국내 이슈 우선)
- 🚫 필터링: 범죄, 연예인 사생활, 정치 편향, 미확인 루머 자동 제외

**출력**: JSON 형식의 콘텐츠 브리프

---

### ✍️ 작가 — 이작가

> "친구한테 카톡 보내듯 편하게, 근데 내용은 진짜 있게."

**모델**: Gemini 2.5-flash → Groq Llama 3.3 70B 폴백 · temperature 0.7 (블로그 0.88)
**페르소나**: 40대 BMW 딜러 직원 '시아아빠' — 매일 아침 뉴스 읽고 느낀 점 기록
**담당**:
- 카드뉴스 글 **5개** (350~450자 + 해시태그 8개)
- 블로그 아티클 1개 (700~900자, 대화체 소제목 2개)
- **source_facts 기반 작성** — 원문에 없는 수치·이름·날짜 창작 금지
- 품질 5단계 후처리:
  1. 블랙리스트 감지 → 재생성 ("와 이거 실화야" 등 상투적 표현)
  2. 제목-본문 키워드 불일치 감지 → 재생성
  3. 깨진 자모·한자 혼입·격식체 혼입 등 패턴 감지 → 재생성
  4. 해시태그 위치 교정 → 본문 중간 해시태그 자동 끝으로 이동
  5. 해시태그 수 검증 → 8개 미만이면 재생성

**출력**: 카드뉴스 5개 + 블로그 아티클

---

### 🎨 디자이너 — 최디자

> "글보다 먼저 눈을 사로잡는 이미지, 제 전문입니다."

**모델**: Groq Llama 3.3 70B (프롬프트 생성) + Pollinations.ai Flux (이미지 생성)
**담당**:
- 5개 헤드라인용 영문 프롬프트 API 1회 호출로 일괄 생성
- Pollinations.ai로 **768×768 이미지 5장** 생성 (최대 3회 재시도)
- 밝고 모던한 SNS 카드뉴스 스타일 (Bloomberg / Wired 톤)
- 이미지 생성 실패 시 `fallback.png` 자동 대체 — `url`/`path` None 노출 없음
- `docs/images/{날짜}_image_{n}.png` 로컬 저장

**출력**: 이미지 5장 (`https://siadaddy.github.io/youngs/images/`)

---

### 🎵 음악 큐레이터 — 한뮤직

> "오늘 하루 어울리는 음악, 제가 골라드릴게요."

**모델**: `ask_gemini25_first()` — Gemini 2.5-flash 직접 (2.0-flash 스킵) → Groq 폴백 · temperature 0.85 · JSON 모드
**수집 주기**: **주 1회** (마지막 수집이 7일 미만이면 스킵)
**담당**:

| 장르 | 색상 | 설명 |
|------|------|------|
| 2000s힙합 | 황금 | 2000~2009 미국/영국 힙합 명곡 10곡 |
| 최신힙합 | 보라 | 2020년 이후 해외 힙합 10곡 |
| 러닝업템포 | 민트 | BPM 140~180 운동·러닝용 10곡 |
| K-pop | 핑크 | 최근 3년 남자 아이돌/솔로 10곡 |
| 여성발라드 | 하늘 | 한국/팝 여성 보컬 발라드 10곡 |
| 걸그룹 | 빨강 | 최근 3년 K-pop 걸그룹 10곡 |
| 최신곡 | 시안 | 2024~2025 해외 팝·R&B 10곡 |

- 장르별 개별 호출 (10곡씩 7회) → JSON 잘림 방지
- 손상된 JSON 자동 복구 (`_extract_songs()`) — 잘린 JSON도 유효한 곡만 추출
- 실패 시 전날 music.json 유지 (파이프라인 영향 없음)

**출력**: `docs/music.json` + `docs/music_YYYY-MM-DD.json` (날짜별 보관, 30일 자동 삭제)

---

### 🎶 YouTube Music 자동 플레이리스트

**파일**: `docs/youtube_playlist.py`
**동작**:
- `playlist_state.json`에 플레이리스트 ID와 추가된 곡 목록을 영구 보관
- "AI 추천 플레이리스트" 이름으로 고정 플레이리스트 하나만 유지
- 날마다 새 곡만 추가 — 이미 추가된 곡은 자동 건너뜀 (57곡 누적)
- `video_cache.json`으로 videoId 캐시 → YouTube 검색 API 할당량 절약
- 할당량 초과 시 중간에 멈춰도 진행분 보존 (추가할 때마다 state 저장)
- **할당량**: 하루 100회 검색 (각 100 unit) — 리셋 시각 오후 4시 KST

**수동 실행**:
```bash
cd ~/바이브코딩/docs && python3 youtube_playlist.py
```

---

### 📤 퍼블리셔 — 정퍼블

> "만들어진 콘텐츠를 가장 보기 좋게 정리하는 건 저의 몫입니다."

**모델**: 없음 (GitHub API 직접 호출)
**담당**:
- `docs/content.json` 생성 (카드뉴스 5개 + 블로그 + 이미지 URL + 수집 뉴스)
- `docs/archive.json` 날짜 목록 업데이트
- `git add / commit / push` → GitHub Pages 자동 반영

**출력**: GitHub Pages 즉시 배포

---

## 🗂 파일 구조

```
바이브코딩/
│
├── 뉴스레터/
│   ├── newsletter_naver.py     ← RSS 뉴스 수집 + 카테고리 분류
│   ├── .env                    ← API 키
│   ├── YYYY-MM-DD.md           ← 날짜별 뉴스레터 백업
│   └── YYYY-MM-DD_data.json    ← AI 크리에이터용 구조화 데이터
│
└── ai-crew/
    ├── main.py                 ← 오케스트레이터 / 단계별 3회 자동 재시도
    ├── run_daily.sh            ← launchd 실행 스크립트
    ├── crew.log                ← 실행 로그
    ├── agents/
    │   ├── planner.py          ← 🎯 기획자 (5개 선정, source_facts 생성)
    │   ├── writer.py           ← ✍️  작가 (카드뉴스 5개, 블로그, 5단계 품질 체크)
    │   ├── designer.py         ← 🎨 디자이너 (768×768, Pollinations.ai, fallback 자동)
    │   └── music_curator.py    ← 🎵 음악 큐레이터 (7장르×10곡, 주1회, docs/music.json)
    └── utils/
        ├── gemini_client.py    ← Gemini/Groq 통합 클라이언트 (ask_gemini / ask_gemini25_first)
        └── notion_reader.py    ← 로컬 .md 파일 직접 읽기

docs/                           ← GitHub Pages 루트
├── index.html                  ← 3탭 메인 사이트
├── about.html                  ← AI 직원 소개
├── music.html                  ← 갤럭시 3D 뮤직 유니버스 (Three.js, YouTube 인앱 재생)
├── content.json                ← 오늘 최신 콘텐츠
├── archive.json                ← 날짜 목록 (최대 60일)
├── music.json                  ← 주간 음악 목록 (70곡)
├── video_cache.json            ← 곡→videoId 캐시 (119곡)
├── playlist_state.json         ← YouTube 플레이리스트 ID + 추가된 곡
├── trades.json                 ← 코인 매매 기록
├── content/
│   └── YYYY-MM-DD.json         ← 날짜별 아카이브
└── images/
    └── YYYY-MM-DD_image_N.png  ← AI 생성 이미지 (영구 저장)
```

---

## 🔧 .env 설정

```
GROQ_API_KEY=...           # 라운드로빈 — 요청마다 key1→2→3→4 순환
GROQ_API_KEY_2=...
GROQ_API_KEY_3=...
GROQ_API_KEY_4=...
GEMINI_API_KEY=...         # Gemini 2.5-flash 우선 (음악 큐레이터)
GEMINI_API_KEY_2=...       # 키1 실패 시 폴백
NEWSLETTER_DIR=/Users/youngchulyu/바이브코딩/뉴스레터
NTFY_TOPIC=siadad-aicrew
```

---

## 🛠 사용 기술 & 비용

| 기술 | 용도 | 비용 |
|------|------|------|
| RSS 피드 (feedparser) | 뉴스 수집 (8개 언론사) | 무료 |
| Gemini 2.5-flash | 음악 큐레이터 (주 1회, 7장르 7회 호출) | 무료 |
| Groq Llama 3.3 70B | 텍스트 생성 전반 (키 4개 라운드로빈) | 무료 |
| Pollinations.ai Flux | AI 이미지 생성 768×768 (키 불필요) | 무료 |
| YouTube Data API v3 | 음악 검색 + IFrame 재생 | 무료 |
| Three.js (WebGL) | 갤럭시 3D 뮤직 유니버스 | 무료 |
| GitHub Pages | 콘텐츠 호스팅 + 3탭 사이트 | 무료 |
| ntfy.sh | 완료 알림 | 무료 |
| **합계** | | **$0** |

---

## 🌐 GitHub Pages 사이트

**라이브 사이트**: `https://siadaddy.github.io/youngs/`

- 매일 `main.py` 실행 완료 후 **자동 git push**
- 날짜 네비게이션으로 **과거 콘텐츠 아카이브** 탐색 (최대 60일)
- **3탭 구성**: 📰 AI 뉴스레터 · 🤖 코인 트레이더 · 🌌 뮤직 유니버스
- **라이브 위젯**: 시계, 날씨, 미세먼지, 환율, 공포탐욕지수
- **🌌 뮤직 유니버스**: Three.js 갤럭시 3D, 7장르 70곡 별자리, YouTube 인앱 재생 (오토플레이)

---

## 🛡 콘텐츠 품질 보호 장치

| 레이어 | 내용 |
|--------|------|
| 뉴스 수집 | RSS 중복 제목 70% 이상 유사 시 자동 제거 |
| 기획자 필터 | 범죄, 연예인 사생활, 정치 편향, 미확인 루머 자동 제외 |
| 기획자 중복 제거 | 제목 키워드 70% 이상 겹치면 첫 번째만 유지 |
| source_facts | 원문 확인 사실만 추출 → 작가가 이것만 사용하도록 강제 |
| 작가 후처리 | 블랙리스트 → 제목-본문 불일치 → 문장 품질 순서로 5단계 감지·재생성 |
| 언어 필터 | CJK, 일본어, 아랍어, 태국어, 러시아어, 힌디어 자동 제거 |

---

## 🔄 자동 재시도 구조

| 단계 | 실패 시 동작 |
|------|-------------|
| 뉴스레터 로드 | 3회 재시도 → 모두 실패 시 종료 + 알림 |
| 기획자 | 3회 재시도 → 모두 실패 시 종료 + 알림 |
| 작가 | 3회 재시도 → 모두 실패 시 종료 + 알림 |
| 디자이너 | 3회 재시도 → 실패해도 빈 이미지로 계속 진행 |
| 음악 큐레이터 | 3회 재시도 → 실패해도 무시 (전날 music.json 유지) |
| GitHub 배포 | 3회 재시도 → 모두 실패 시 종료 + 알림 |
| Gemini 429 | 30~65초 대기 후 다음 키 전환 |
| Groq 429 | 즉시 다음 키로 전환 (key1→2→3→4 라운드로빈) |

---

## 🚀 수동 실행

```bash
# 전체 파이프라인
/Users/youngchulyu/바이브코딩/ai-crew/run_daily.sh

# 뉴스레터만
cd /Users/youngchulyu/바이브코딩/뉴스레터
python3 newsletter_naver.py

# AI 크리에이터만 (뉴스레터 파일 있을 때)
cd /Users/youngchulyu/바이브코딩/ai-crew
python3 main.py

# 음악 큐레이터만
cd /Users/youngchulyu/바이브코딩/ai-crew
python3 -c "from agents import music_curator; music_curator.save(music_curator.run())"

# 유튜브 플레이리스트 업데이트
cd /Users/youngchulyu/바이브코딩/docs
python3 youtube_playlist.py

# 로그 확인
tail -f /Users/youngchulyu/바이브코딩/ai-crew/crew.log
```

---

## 📝 업데이트 로그

### 2026-04-19
- **Chrome 오토플레이 차단 수정** (`docs/music.html`): 페이지 로드 시 video_cache.json 미리 fetch → 클릭 시 동기 `loadVideoById()` 호출로 재생 정상화

### 2026-04-18
- **뮤직 유니버스 전면 개편** (`docs/music.html`): 갤럭시 디스크 Gaussian 배치, 플레이 링 위치 버그 수정, 플레이리스트 패널 전체 곡 표시
- **음악 장르 7개로 재편**: 2000s힙합·최신힙합·러닝업템포·K-pop·여성발라드·걸그룹·최신곡 (각 10곡)
- **음악 수집 주 1회 전환**: `_should_run_music()` — 7일 미만이면 스킵
- **`ask_gemini25_first()` 추가**: Gemini 2.0-flash RPM 429 완전 회피

### 2026-04-17
- **음악 큐레이터 장르 개편**: K-pop 위주 → 다장르 균형 수집
- **음악 큐레이터 JSON 복구 로직**: `_extract_songs()` 추가
- **YouTube Music 누적 플레이리스트**: 고정 플레이리스트에 신곡만 추가
- **AI 모델 전략 변경**: Gemini 우선 + Groq 폴백 (gemini_client.py 전면 재작성)
- **Gemini 이중 키**: GEMINI_API_KEY + GEMINI_API_KEY_2 순차 시도

### 2026-04-14
- **Groq 전체 키 소진 대응**: 4개 키 모두 429 시 90초 대기 후 재시도
- **작가 품질 게이트 전면 개편**: `quality_check()` 통합 함수 도입

### 2026-04-12
- **뉴스 수집 분리**: 06:40 별도 LaunchAgent
- **Groq 키 4개**: key1~4 라운드로빈
- **작가 품질 5단계**: 해시태그 위치 교정 + 해시태그 수 검증 추가

### 2026-04-09
- **뮤직 유니버스 탭 승격**: 3D 별자리 → 메인 탭

### 2026-04-08
- **음악 큐레이터 에이전트 신규** + **뮤직 유니버스 신규**

### 2026-03-25
- 시스템 최초 구축

---

*최종 업데이트: 2026-04-19 | Powered by Gemini 2.5-flash + Groq + Pollinations.ai + YouTube API + Three.js + GitHub Pages*
