# 🤖 시아아빠님의 AI 크리에이터

> 매일 아침, AI 직원들이 뉴스를 읽고 콘텐츠를 만들어 노션과 GitHub Pages에 올려드립니다.

---

## 📋 시스템 개요

네이버 뉴스 API로 수집한 뉴스레터를 바탕으로, 역할이 다른 AI 에이전트들이 협업해
카드뉴스 5개 + 블로그 아티클 + 이미지 5장을 자동 생성하고 노션 + GitHub Pages에 업로드합니다.

**실행 환경**: MacBook (launchd) — 서버 불필요, 완전 로컬 자동화

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
                기획자 → 작가 → 디자이너 → 노션 퍼블리셔
                → docs/images/ 저장 → GitHub Pages 자동 push
                → 금요일엔 주간 브리핑도 자동 추가
                각 단계 실패 시 최대 3회 자동 재시도

~08:00 KST  ✅ 모든 작업 완료
             📱 ntfy 앱으로 완료 알림 수신
```

**절전 대응**: `sudo pmset repeat wakeorpoweron MTWRFSU 06:55:00` 으로 맥북 자동 깨움

---

## 👥 AI 직원 소개

### 🎯 기획자 — 박기획

> "오늘 어떤 뉴스가 사람들 마음을 움직일까요?"

**역할**: 뉴스레터 전문을 분석해 카드뉴스와 블로그에 최적화된 콘텐츠 브리프 작성
**모델**: Groq — Llama 3.3 70B
**담당**:
- 오늘 뉴스 중 핵심 뉴스 **5개** 선정 (중복 주제 자동 금지)
- 첫 번째 카드는 반드시 **자동차/BMW/전기차** 관련
- 각 뉴스의 각도(angle), 톤, 키워드, **원문 확인 사실(source_facts)** 기획
- 블로그 아티클 주제 1개 + source_facts 선정
- 🚫 필터링: 범죄 전력 연예인, 자극적 사건사고, 정치 편향, 미확인 루머 자동 제외

**출력**: JSON 형식의 콘텐츠 브리프 (정규식 기반 안전 파싱)

---

### ✍️ 작가 — 이작가

> "독자가 손을 멈추고 읽게 만드는 첫 줄, 제가 씁니다."

**역할**: 기획자의 브리프를 받아 카드뉴스 글과 블로그 아티클 작성
**모델**: Groq — Llama 3.3 70B (temperature 0.7)
**담당**:
- 카드뉴스 글 **5개** (각 최소 500자)
  - 훅 → 배경 → `[사실]` 팩트 → `[분석]` / `[전망]` → 행동유도 → 해시태그 10개
  - **source_facts 기반 작성** — 원문에 없는 수치·이름·날짜 창작 금지
- 블로그 아티클 1개 (마크다운, 1500자+, 소제목 4개 이상)
  - 블로그도 **source_facts 기반** — 불확실한 내용은 "~로 알려졌다" 표현 사용
- 카드 간 20초 대기 (Groq TPM 한도 대응)
- 아티클 미완성 자동 감지 → 이어서 완성

**출력**: 카드뉴스 5개 + 블로그 아티클

---

### 🎨 디자이너 — 최디자

> "글보다 먼저 눈을 사로잡는 이미지, 제 전문입니다."

**역할**: 뉴스 헤드라인에 맞는 이미지 프롬프트 생성 → AI 이미지 생성 → GitHub Pages 저장
**모델**: Groq — Llama 3.3 70B (프롬프트 생성) + Stable Horde (이미지 생성, 무료)
**담당**:
- 5개 헤드라인용 영문 프롬프트 API 1회 호출로 일괄 생성
- Stable Horde(익명 키, 무료)로 **768×768 이미지 5장** 생성
- `docs/images/{날짜}_image_{n}.png` 로컬 저장
- GitHub Pages URL 반환 → 노션 이미지 블록으로 직접 임베드

**출력**: 이미지 5장 (`https://siadaddy.github.io/youngs/images/`)

---

### 📤 노션 퍼블리셔 — 정퍼블

> "만들어진 콘텐츠를 가장 보기 좋게 정리하는 건 저의 몫입니다."

**역할**: 모든 에이전트의 결과물을 받아 노션 페이지로 통합 업로드
**모델**: 없음 (Notion API 직접 호출)
**담당**:
- **새 페이지 생성** (매일, 기존 페이지에 덮어쓰지 않음)
- 상단: 카드뉴스 5개 (이미지 → 글 순서) + **AI 에디터 PICK** (블로그 아티클)
- 하단: 오늘 수집된 뉴스 목록 (출처 레이블 + 기사 링크 포함)
- 2000자 초과 텍스트 자동 분할 (Notion API 한도 대응)

**출력**: 노션 페이지 1개 (제목: 🤖 YYYY년 MM월 DD일)

---

### 📅 주간 브리퍼 — 한주간

> "한 주를 5분으로 요약합니다. 바쁘신 분들을 위해."

**역할**: 매주 금요일, 이번 주 뉴스레터 5일치를 읽고 주간 종합 브리핑 생성
**모델**: Groq — Llama 3.3 70B (temperature 0.65)
**담당**:
- 월~금 뉴스레터 .md 파일 수집 (각 최대 3000자)
- 주간 TOP 5 뉴스 선정 + AI/기술·경제·글로벌·자동차 섹션별 분석
- 한 주 인사이트 칼럼 작성
- **원문 기반 사실만 사용** — 수치·이름 창작 금지

**출력**: 주간 브리핑 노션 페이지 (제목: 📅 주간 브리핑 — MM/DD ~ MM/DD)

---

## 🗂 파일 구조

```
/Users/youngchulyu/
│
├── README.md                   ← GitHub Pages 레포 루트
├── docs/
│   ├── index.html              ← 라이브 사이트 메인 페이지
│   ├── content.json            ← 오늘 최신 콘텐츠
│   ├── archive.json            ← 날짜 목록 (최대 60일)
│   ├── content/
│   │   ├── 2026-03-28.json     ← 날짜별 아카이브
│   │   └── ...
│   └── images/
│       ├── 2026-03-28_image_1.png  ← AI 생성 이미지 (영구 저장)
│       └── ...
│
├── app.py                      ← Instacart 대시보드 (Streamlit)
├── requirements.txt            ← Streamlit 앱 의존성
│
└── 바이브코딩/
    ├── 뉴스레터/
    │   ├── newsletter_naver.py     ← 뉴스 수집 + AI 요약 / Groq key1→key2 폴백
    │   ├── .env                    ← NAVER + GROQ 키
    │   ├── 2026-03-28.md           ← 날짜별 뉴스레터 백업
    │   └── 2026-03-28_data.json    ← AI 크리에이터용 구조화 데이터
    │
    └── ai-crew/
        ├── main.py                 ← 오케스트레이터 / 단계별 3회 자동 재시도
        ├── run_daily.sh            ← launchd 실행 스크립트
        ├── crew.log                ← 실행 로그
        ├── agents/
        │   ├── planner.py          ← 🎯 기획자 (5개 선정, source_facts 생성)
        │   ├── writer.py           ← ✍️  작가 (카드뉴스 5개, 블로그, temperature 0.7)
        │   ├── designer.py         ← 🎨 디자이너 (768×768, docs/images/ 저장)
        │   ├── notion_publisher.py ← 📤 퍼블리셔 (AI 상단 / 뉴스 하단)
        │   └── weekly_briefer.py   ← 📅 주간 브리퍼 (금요일)
        ├── utils/
        │   ├── gemini_client.py    ← Groq API 클라이언트 (key1→key2 폴백, 외국어 필터)
        │   └── notion_reader.py    ← 로컬 .md 파일 직접 읽기
        └── .env                    ← GROQ + NOTION + NTFY 키
```

---

## 🔧 .env 설정

### `/바이브코딩/뉴스레터/.env`
```
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
GROQ_API_KEY=...          # key1 소진 시 key2 자동 전환
GROQ_API_KEY_2=...
```

### `/바이브코딩/ai-crew/.env`
```
GROQ_API_KEY=...
GROQ_API_KEY_2=...        # key1 소진 시 자동 전환
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
| Groq (Llama 3.3 70B) | 텍스트 생성 전반 (키 2개 폴백) | 무료 |
| Stable Horde | AI 이미지 생성 768×768 | 무료 |
| GitHub Pages | 이미지 영구 호스팅 + 사이트 | 무료 |
| Notion API | 콘텐츠 저장 | 무료 |
| ntfy.sh | 완료 알림 | 무료 |
| Streamlit Community Cloud | Instacart 대시보드 배포 | 무료 |
| Google Drive | DuckDB 파일 호스팅 | 무료 |
| **합계** | | **$0** |

---

## 🌐 GitHub Pages 사이트

**라이브 사이트**: `https://siadaddy.github.io/youngs/`

- 매일 `main.py` 실행 완료 후 **자동 git push**
- 날짜 네비게이션으로 **과거 콘텐츠 아카이브** 탐색 (최대 60일)
- **라이브 대시보드**: 시계, 날씨, 미세먼지, 환율, 공포탐욕지수
- **TradingView 티커**: KOSPI, 삼성전자, S&P500, 나스닥, 달러/원, BTC, 금
- **내 제작물** 섹션: Instacart 대시보드 연결

---

## 📱 알림 설정 (ntfy)

1. 아이폰 App Store에서 **ntfy** 검색 → 설치
2. 앱 열고 **"+"** → 토픽: `siadad-aicrew` 입력
3. 매일 아침 8시 전후로 완료 알림 수신

---

## 🚀 수동 실행

```bash
# 전체 파이프라인 수동 실행 (뉴스레터 수집 + AI 크리에이터)
/Users/youngchulyu/바이브코딩/ai-crew/run_daily.sh

# 뉴스레터만 수동 실행
cd /Users/youngchulyu/바이브코딩/뉴스레터
python3 newsletter_naver.py

# AI 크리에이터만 수동 실행 (뉴스레터 파일 있을 때)
cd /Users/youngchulyu/바이브코딩/ai-crew
python3 main.py

# 로그 확인
tail -f /Users/youngchulyu/바이브코딩/ai-crew/crew.log
```

---

## 📊 노션 페이지 구조

```
뉴스레터 (부모 페이지)
│
├── 🤖 2026년 03월 28일  ← AI 크리에이터 페이지 (매일 새 페이지)
│     ├── 📰 오늘의 카드뉴스 #1 ~ #5
│     │     ├── 이미지 (768×768, GitHub Pages URL 임베드)
│     │     └── 글 ([사실] / [분석] / [전망] + 해시태그 10개)
│     ├── 🧠 AI 에디터 PICK (블로그 아티클, 마크다운)
│     └── 📰 오늘 수집된 뉴스
│           ├── 🏆 AI 선정 TOP 3
│           └── 카테고리별 뉴스 목록 (링크 포함)
│
└── 📅 주간 브리핑 — 03/24 ~ 03/28  ← 금요일에만 자동 생성
      ├── 🏆 이번 주 TOP 5
      ├── 🤖 AI/기술 동향
      ├── 💰 경제/시장 흐름
      ├── 🚗 자동차/모빌리티
      └── 💡 이번 주 인사이트
```

---

## 🔄 자동 재시도 구조

| 단계 | 실패 시 동작 |
|------|-------------|
| 뉴스레터 로드 | 3회 재시도 → 모두 실패 시 종료 + 알림 |
| 기획자 | 3회 재시도 → 모두 실패 시 종료 + 알림 |
| 작가 | 3회 재시도 → 모두 실패 시 종료 + 알림 |
| 디자이너 | 3회 재시도 → 실패해도 빈 이미지로 계속 진행 |
| 노션 저장 | 3회 재시도 → 모두 실패 시 종료 + 알림 |
| 주간 브리핑 | 3회 재시도 → 실패해도 무시하고 완료 처리 |
| Groq 429 오류 | retry-after 대기 후 재시도 (최대 90초) → key2 자동 전환 |

재시도 간격: **10초**

---

## 🛡 콘텐츠 품질 보호 장치

| 레이어 | 내용 |
|--------|------|
| 뉴스 수집 | 범죄·사건사고 키워드 제외 (재난/안전 키워드로 교체) |
| 기획자 필터 | 범죄 전력 연예인, 자극적 사건사고, 정치 편향, 미확인 루머 자동 제외 |
| source_facts | 원문 확인 사실만 추출 → 작가가 이것만 사용하도록 강제 |
| 언어 필터 | CJK, 일본어, 아랍어, 태국어, 러시아어, 힌디어 자동 제거 |
| JSON 파싱 | 정규식으로 JSON 블록만 추출 (앞뒤 설명 텍스트 무시) |
| 이미지 생성 | Stable Horde generations 빈 배열 체크 → 크래시 없이 실패 처리 |

---

## 🐛 트러블슈팅

| 증상 | 확인 사항 |
|------|---------|
| 파이프라인 미실행 | `crew.log` 확인, launchd 상태: `launchctl list \| grep aicrew` |
| Groq 429 계속 | 일일 쿼터 소진 → 내일 자동 리셋, key2 자동 전환 확인 |
| 이미지 안 보임 | Stable Horde 지연 or GitHub Pages 미push → 수동 `git push origin main` |
| GitHub Pages 미반영 | `git push origin main` 수동 실행 |
| 노션 중복 페이지 | newsletter_naver.py Notion 업로드는 비활성화 상태 (ai-crew가 통합 처리) |

---

## 📝 업데이트 로그

### 2026-03-28
- **콘텐츠 품질 강화**: 전체 파이프라인 안정성 점검 및 수정
  - designer.py: Stable Horde generations 빈 배열 크래시 방지
  - planner.py: JSON 정규식 파싱 — Groq 응답에 앞뒤 텍스트 있어도 안전
  - newsletter_naver.py: _sanitize 일본어·러시아어·힌디어 필터 추가
  - newsletter_naver.py: 사건/사고 키워드 범죄→재난/안전으로 교체
  - newsletter_naver.py: Groq key2 fallback 추가
  - weekly_briefer.py: 원문 기반 사실만 사용, 수치 창작 금지 추가
- **작가 개선**: 해시태그 20개 → 10개 (핵심만, 중복 금지), temperature 0.85 → 0.7
- **블로그 아티클 source_facts 적용**: 기획자가 블로그용 원문 사실도 생성

### 2026-03-27
- **맥북 launchd로 전환**: GitHub Actions cron 제거 → 로컬 자동화
  - `run_daily.sh` + `com.siadad.aicrew.plist` 신규 생성
  - `sudo pmset repeat wakeorpoweron MTWRFSU 06:55:00` 절전 대응
- **이미지 호스팅 변경**: freeimage.host → GitHub Pages `docs/images/` 영구 저장
- **Groq 듀얼 키**: GROQ_API_KEY_2 추가, key1 소진 시 자동 전환
- **외국어 오염 방지**: _sanitize 일본어·러시아어·힌디어 필터 추가
- **hallucination 방지**: planner source_facts → writer 원문 기반 작성 강제
- **기획자 필터 강화**: 조진웅 사태 계기 — 범죄 전력 연예인, 자극적 뉴스 자동 제외
- **Instacart 대시보드**: app.py Streamlit + Google Drive gdown 연동
- **사이트 개선**: TradingView 티커 추가, GitHub 버튼 위치 변경, AI 에디터 PICK 명칭 변경
- **"내 제작물" 섹션**: Instacart 대시보드 카드 추가

### 2026-03-26
- 카드뉴스 3개 → **5개** 확대 (중복 주제 자동 금지)
- 카드뉴스 글 형식 강화: `[사실]` · `[분석]` · `[전망]` 레이블, 출처 명시
- 이미지 3장 → **5장** (768×768, Cinematic editorial 스타일)
- 노션 페이지 구조: AI 콘텐츠 **상단** / 수집 뉴스 **하단** (출처·링크 포함)
- 뉴스레터 읽기: Notion API → **로컬 .md 파일** 직접 읽기
- 각 단계 실패 시 **자동 재시도** (최대 3회, 10초 간격)
- ntfy 알림: 한글 헤더 인코딩 오류 → **JSON 방식** 전환
- **GitHub Pages 배포**: 날짜별 아카이브 + AI 직원 소개 포함

### 2026-03-25
- 시스템 최초 구축
- Groq (Llama 3.3 70B) + Stable Horde + Notion API 연동
- ntfy.sh 완료 알림 설정

---

*최종 업데이트: 2026-03-28 | Powered by Groq + Stable Horde + Notion API + GitHub Pages*
