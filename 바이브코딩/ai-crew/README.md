# 🤖 시아아빠님의 AI 크리에이터

> 매일 아침, AI 직원들이 뉴스를 읽고 콘텐츠를 만들어 GitHub Pages에 자동 배포합니다.

**라이브 사이트**: https://siadaddy.github.io/youngs/

---

## 📋 시스템 개요

RSS 피드로 수집한 뉴스를 바탕으로, 역할이 다른 AI 에이전트들이 협업해
카드뉴스 5개 + 블로그 아티클 + 이미지 5장 + 오늘의 음악 70곡+을 자동 생성하고 GitHub Pages에 배포합니다.

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
                기획자 → 작가 → 디자이너 → 음악 큐레이터 → GitHub 배포
                → docs/images/ 저장 → GitHub Pages 자동 push
                각 단계 실패 시 최대 3회 자동 재시도

~07:20 KST  ✅ 모든 작업 완료
             📱 ntfy 앱으로 완료 알림 수신
```

**절전 대응**: `sudo pmset repeat wakeorpoweron MTWRFSU 06:35:00` 으로 맥북 자동 깨움

---

## 👥 AI 직원 소개

### 🎯 기획자 — 박기획

> "오늘 어떤 뉴스가 사람들 마음을 움직일까요?"

**모델**: Groq — Llama 3.3 70B · temperature 0.65 · JSON 모드
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

**모델**: Groq — Llama 3.3 70B · temperature 0.7 (블로그 0.88)
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

**모델**: Groq — Llama 3.3 70B (프롬프트 생성) + Pollinations.ai Flux (이미지 생성)
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

**모델**: Gemini 우선 → 실패 시 Groq 폴백 · temperature 0.85 · JSON 모드
**담당**:
- 2000년대 힙합 15곡 / 최신 힙합 10곡 / 러닝·업템포 25곡 / K-pop 25곡 / 여성 보컬 발라드 25곡
- 한 아티스트 최대 3곡 | 트롯·클래식·동요 제외 | 100곡 큐레이션 목표
- 손상된 JSON 자동 복구 (`_extract_songs()`) — Gemini가 잘린 JSON 반환해도 유효한 곡만 추출
- 실패 시 전날 music.json 유지 (파이프라인 영향 없음)

**출력**: `docs/music.json` + `docs/music_YYYY-MM-DD.json` (날짜별 보관, 30일 자동 삭제)

### 🎶 YouTube Music 자동 플레이리스트

**파일**: `docs/youtube_playlist.py`
**동작**:
- `playlist_state.json`에 플레이리스트 ID와 추가된 곡 목록을 영구 보관
- "AI 추천 플레이리스트" 이름으로 고정 플레이리스트 하나만 유지
- 날마다 새 곡만 추가 — 이미 추가된 곡은 자동 건너뜀
- `video_cache.json`으로 videoId 캐시 → YouTube 검색 API 할당량 절약
- 할당량 초과 시 중간에 멈춰도 진행분 보존 (추가할 때마다 state 저장)
- **할당량**: 하루 100회 검색 (각 100 unit) — 리셋 시각 오후 4시 KST (PDT 기준 자정)

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
│   ├── newsletter_rss.py       ← RSS 뉴스 수집 + Groq 요약
│   ├── .env                    ← GROQ 키
│   ├── YYYY-MM-DD.md           ← 날짜별 뉴스레터 백업
│   └── YYYY-MM-DD_data.json    ← AI 크리에이터용 구조화 데이터
│
└── ai-crew/
    ├── main.py                 ← 오케스트레이터 / 단계별 3회 자동 재시도
    ├── run_daily.sh            ← launchd 실행 스크립트
    ├── crew.log                ← 실행 로그
    ├── agents/
    │   ├── planner.py          ← 🎯 기획자 (5개 선정, source_facts 생성)
    │   ├── writer.py           ← ✍️  작가 (카드뉴스 5개, 블로그, 3단계 품질 체크)
    │   ├── designer.py         ← 🎨 디자이너 (768×768, Pollinations.ai, fallback 자동)
    │   └── music_curator.py    ← 🎵 음악 큐레이터 (70곡+, docs/music.json)
    └── utils/
        ├── gemini_client.py    ← Groq API 클라이언트 (key1~4 라운드로빈, 외국어 필터)
        └── notion_reader.py    ← 로컬 .md 파일 직접 읽기

docs/                           ← GitHub Pages 루트
├── index.html                  ← 3탭 메인 사이트
├── about.html                  ← AI 직원 소개
├── music.html                  ← 뮤직 유니버스 (Three.js)
├── content.json                ← 오늘 최신 콘텐츠
├── archive.json                ← 날짜 목록 (최대 60일)
├── music.json                  ← 오늘의 음악 목록
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
NEWSLETTER_DIR=/Users/youngchulyu/바이브코딩/뉴스레터
NTFY_TOPIC=siadad-aicrew
```

---

## 🛠 사용 기술 & 비용

| 기술 | 용도 | 비용 |
|------|------|------|
| RSS 피드 (feedparser) | 뉴스 수집 (8개 언론사) | 무료 |
| Groq Llama 3.3 70B | 텍스트 생성 전반 · 음악 큐레이션 (키 4개 라운드로빈) | 무료 |
| Pollinations.ai Flux | AI 이미지 생성 768×768 (키 불필요) | 무료 |
| YouTube Data API v3 | 음악 검색 + IFrame 재생 | 무료 |
| iTunes API | 앨범아트 조회 | 무료 |
| Three.js (WebGL) | 3D 뮤직 유니버스 | 무료 |
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
- **🌌 뮤직 유니버스**: Three.js 3D 은하, AI 큐레이션 음악, YouTube 인앱 재생

---

## 🛡 콘텐츠 품질 보호 장치

| 레이어 | 내용 |
|--------|------|
| 뉴스 수집 | RSS 중복 제목 70% 이상 유사 시 자동 제거 |
| 기획자 필터 | 범죄, 연예인 사생활, 정치 편향, 미확인 루머 자동 제외 |
| 기획자 중복 제거 | 제목 키워드 70% 이상 겹치면 첫 번째만 유지 |
| source_facts | 원문 확인 사실만 추출 → 작가가 이것만 사용하도록 강제 |
| 작가 후처리 | 블랙리스트 → 제목-본문 불일치 → 문장 품질 순서로 3단계 감지·재생성 |
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
| Groq 429 오류 | 즉시 다음 키로 전환 (key1→2→3→4 라운드로빈) |

---

## 🚀 수동 실행

```bash
# 전체 파이프라인
/Users/youngchulyu/바이브코딩/ai-crew/run_daily.sh

# 뉴스레터만
cd /Users/youngchulyu/바이브코딩/뉴스레터
python3 newsletter_rss.py

# AI 크리에이터만 (뉴스레터 파일 있을 때)
cd /Users/youngchulyu/바이브코딩/ai-crew
python3 main.py

# 로그 확인
tail -f /Users/youngchulyu/바이브코딩/ai-crew/crew.log
```

---

## 📝 업데이트 로그

### 2026-04-14
- **Groq 전체 키 소진 대응**: `gemini_client.py` — 4개 키 모두 429 시 90초 대기 후 최대 2회 글로벌 재시도 추가 (TPM 윈도우 리셋 대응)
- **작가 품질 게이트 전면 개편**: `quality_check()` 통합 함수 도입 — 블랙리스트·제목-본문 불일치·패턴·해시태그·반복 표현 모두 단일 함수로 처리, 재생성 시 targeted hint 삽입
- **기획자 프롬프트 강화**: 의료/제약 단순 정책 뉴스 제외, 5개 카드 중복 기업·사건 구체 예시 추가
- **music3d.html 추가**: 디스코볼 스타일 3D 뮤직 페이지 (Fibonacci 구면 배치, 네온 글라스 타일, 290개 고밀도)

### 2026-04-12
- **뉴스 수집 분리**: 06:40 별도 LaunchAgent → ai-crew 07:00 즉시 시작 (약 5분 단축)
- **Groq 키 4개**: key1~4 라운드로빈 (ai-crew) / 폴백 체인 (coin-trader)
- **작가 품질 5단계**: 해시태그 위치 교정 + 해시태그 수 검증 추가
- **음악 큐레이터 장르 균형**: K-pop 20 / 한국인디 20 / 팝 20 / R&B 15 / 기타 5, 발라드 20% 제한
- **디자이너 fallback**: 이미지 실패 시 fallback.png 자동 대체 (None 노출 제거)
- **기획자 강화**: 지자체/소규모홍보 제외, 경제/산업/기술/국제 최소 3개, source_facts 부실 재생성

### 2026-04-11
- **뉴스레터 품질 개선**: 작가 3단계 후처리 추가 (블랙리스트 → 제목-본문 불일치 → 문장 품질)
- **GitHub Pages 섹션 순서 변경**: AI 에디터픽 → 카드뉴스 → 수집뉴스 (훅 우선)
- **about.html 전면 수정**: 나는 누구인가 섹션·한뮤직 직원 카드 추가, 노션·한주간 제거
- **사이트 개선**: OG 메타태그, 승률 카드, 봇 상태 표시, 다크/라이트 토글, 방문자 카운터 등

### 2026-04-09
- **뮤직 유니버스 탭 승격**: 메인 탭으로 이동 (iframe 레이지 로드)
- **3D 우주화**: 별 12,000개·은하수·성운 7개·지구·별똥별
- **노션 발행 중단**: GitHub Pages 단독 배포로 전환

### 2026-04-08
- **음악 큐레이터 에이전트 신규** (`agents/music_curator.py`)
- **뮤직 유니버스 신규** (`docs/music.html`) — Three.js + YouTube API

### 2026-04-03
- **작가 페르소나 변경**: "시아아빠" (40대 BMW 딜러 직원)
- 카드뉴스 자연스러운 대화체, 해시태그 8개, 블로그 700~900자

### 2026-04-01
- **이미지 생성 Stable Horde → Pollinations.ai 전환** (이후 다시 Stable Horde 복귀)
- Groq 413 오류 수정: 뉴스레터 입력 4000자 제한

### 2026-03-31
- 뉴스 수집 **네이버 API → RSS 피드** 전환 (feedparser, 언론사 직접 수집)
- 중복 제목 자동 제거 (유사도 70% 기준)

### 2026-03-27
- **맥북 launchd 전환**: GitHub Actions → 로컬 자동화
- **Groq 듀얼 키**: key1 소진 시 key2 자동 전환

### 2026-03-25
- 시스템 최초 구축

---

### 2026-04-17
- **음악 큐레이터 장르 전면 개편**: K-pop·힙합·인디 → 2000년대힙합·최신힙합·러닝업템포·K-pop·여성발라드 5장르 (100곡)
- **음악 큐레이터 JSON 복구 로직 추가**: `_extract_songs()` — Gemini 잘린 JSON도 유효한 곡 개별 파싱 후 추출
- **음악 큐레이터 경로 버그 수정**: DOCS_PATH `../../../docs` → `../../docs` (저장 위치 바이브코딩/docs로 수정)
- **YouTube Music 누적 플레이리스트**: 매일 새 플레이리스트 생성 → 고정 "AI 추천 플레이리스트" 하나에 신곡만 누적 추가
- **AI 모델 전략 변경**: Gemini 우선 → Groq 폴백 (gemini_client.py 전면 재작성)
- **Gemini 이중 키**: GEMINI_API_KEY + GEMINI_API_KEY_2 순차 시도

---

*최종 업데이트: 2026-04-17 | Powered by Gemini + Groq + Pollinations.ai + YouTube API + Three.js + GitHub Pages*
