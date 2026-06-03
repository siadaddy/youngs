# 시아아빠의 AI 데일리 — Claude Code 컨텍스트
> 마지막 업데이트: 2026-06-03

## 📦 프로젝트 구조

```
/Users/youngchulyu/vibe-coding/   ← 작업 루트
├── coin-trader/                  ← AI 코인 자동매매 (⛔ 2026-05-25 운용 종료)
└── youngs/                       ← git repo (siadaddy.github.io/youngs)
    ├── docs/                     ← GitHub Pages
    │   ├── index.html            ← 메인 대시보드 (히어로·개요·탭·포트폴리오)
    │   ├── about.html            ← AI 직원 소개 & 파이프라인
    │   ├── music.html            ← 뮤직 유니버스 (Three.js 3D)
    │   ├── coin.html             ← 코인봇 종료 기록 대시보드
    │   ├── content/              ← 날짜별 카드뉴스 JSON (YYYY-MM-DD.json)
    │   ├── images/               ← Pollinations.ai 생성 이미지 (30일 자동 정리)
    │   ├── archive.json          ← 발행일 목록 (date-nav에서 로드)
    │   ├── office_memory.json    ← AI 직원 학습 기록 (ai-crew 병합)
    │   ├── weekly_trend.json     ← 주간 트렌드 브리핑 (매주 월요일 갱신)
    │   └── trades.json           ← 코인 매매 기록 (종료 상태 보존)
    ├── ai-crew/                  ← AI 뉴스레터 자동화 (GitHub Actions 매일 06:40 KST)
    │   ├── agents/               ← 박기획·이작가·최디자·한뮤직·AI주간트렌드
    │   ├── utils/agent_memory.py ← Supabase agent_memories 동기화
    │   └── utils/office_export.py← office_memory.json 생성
    └── newsletter/               ← 뉴스 수집 (GitHub Actions 매일 06:40 KST)
```

> `youngs/`가 git root. `git add docs/index.html` 처럼 youngs/ 기준 상대경로 사용.  
> coin-trader는 youngs/ 밖 (`../coin-trader/`). 운용 종료 상태이나 파일 보존 중.

---

## ⚙️ 실행 구조

| 작업 | 방식 | 시간 |
|------|------|------|
| 뉴스 수집 (newsletter) | GitHub Actions | 매일 06:40 KST |
| AI 뉴스레터 (ai-crew) | GitHub Actions (`needs: newsletter`) | 매일 06:40 KST (newsletter 완료 후) |
| 주간 트렌드 | GitHub Actions (매주 월요일) | 06:40 KST |
| 코인 매매 | ⛔ **운용 종료** (2026-05-25) | — |

> GitHub Actions는 fresh checkout → `agent_memory.json` 없음 → `_load()`가 Supabase에서 자동 복구.

---

## 🗄 Supabase 테이블

| 테이블 | 내용 |
|--------|------|
| `news_trends` | 날짜별 TOP3 + category_summaries + talking_points (오늘의 이야깃거리) |
| `news_cards` | 카드뉴스 본문 데이터 |
| `agent_memories` | AI 직원 학습 데이터 — **컬럼 분리**: `agent_name(PK)`, `events(JSONB)`, `diary(JSONB)`, `persona(TEXT)`, `growth_score(INT)`, `persona_updated_at(DATE)`, `updated_at` |

> `agent_memories`는 단일 `data` 컬럼이 **아님**. `_sync_supabase()`는 각 컬럼에 개별 upsert.  
> 로컬 `agent_memory.json` 없을 때 `_load_from_supabase()`로 자동 복구 후 로컬 캐시 저장.

---

## 🔑 API 키 & LLM 전략

- **ai-crew** (`ai-crew/.env`): Gemini 2.5-flash 우선 → Groq 폴백
- **coin-trader** (`../coin-trader/.env`): 운용 종료 (키 보존)

### Supabase 키 주의사항 (2026-06-03 변경)
- GitHub Secret 이름: `SUPABASE_KEY` (service role 키, `sb_secret_...` 형식)
- anon 키(`sb_publis_...`)는 **RLS 정책으로 쓰기 불가** → service role 키 필수
- `newsletter_naver.py`, `agent_memory.py` 모두 env var에서만 읽음 (하드코딩 제거됨)
- 키를 바꿨을 때 GitHub Secret → `SUPABASE_KEY` 값 업데이트 필요

---

## 🎭 AI 사무실 직원 현황

| 직원 | 역할 | 상태 | 파일 |
|------|------|------|------|
| 박기획 | 콘텐츠 기획·주제 선정 | 🟢 active | `agents/planner.py` |
| 이작가 | 블로그 아티클 작성 | 🟢 active | `agents/writer.py` |
| 최디자 | Pollinations.ai 이미지 생성 | 🟢 active | `agents/designer.py` |
| 한뮤직 | 음악 플레이리스트 큐레이션 | 🟢 active | `agents/music_curator.py` |
| AI주간트렌드 | 주간 트렌드 분석 (월요일) | 🟢 active | `agents/weekly_trend.py` |
| AI어드바이저 | 코인 매매 판단 | 🏖️ vacation (운용 종료) | `../coin-trader/agents/ai_advisor.py` |
| 이가드 / 리포터 | 보조 직원 | 🏖️ vacation | 표시 전용 |

> Canvas 픽셀아트에서 vacation 직원은 도트 캐릭터 제외 (`VACATION_CHARS` Set).  
> 5건 이상 일기 누적 시 페르소나 자동 진화. `get_hints()`로 각 에이전트 프롬프트에 반영.

---

## 📚 핵심 파일

| 파일 | 역할 |
|------|------|
| `newsletter/newsletter_naver.py` | 뉴스 수집 + AI 요약 + 오늘의 이야깃거리 → Supabase (TOP3 제외 별도 풀에서 생성) |
| `ai-crew/agents/planner.py` | 카드뉴스 주제 선정 (삼천리 그룹 우선 포함 규칙 적용) |
| `ai-crew/agents/writer.py` | 블로그 아티클 작성 (`get_hints("이작가")` 적용) |
| `ai-crew/agents/designer.py` | 이미지 생성 + 30일 자동 정리 |
| `ai-crew/agents/music_curator.py` | 음악 큐레이션 — **수집 주기 90일(분기)** (`_should_run_music()`) |
| `ai-crew/agents/weekly_trend.py` | 주간 트렌드 (json_mode=False, max_tokens 4096) |
| `ai-crew/utils/agent_memory.py` | 메모리 R/W + Supabase 동기화 + 페르소나 진화 |
| `ai-crew/utils/office_export.py` | office_memory.json 생성 (휴가 에이전트 vacation 상태 보존) |
| `docs/index.html` | 메인 대시보드 — 모바일 640px 최적화 (2026-05-31) |
| `docs/content.json` | **오늘 날짜 카드뉴스 캐시** — 오늘 날짜 표시 시 이 파일에서 captions 로드 |
| `docs/content/YYYY-MM-DD.json` | 날짜별 카드뉴스 — 과거 날짜 조회 시 사용 |
| `ai-crew/quality_log.json` | 카드 품질 검수 로그 (재생성 이력) |

---

## 🌐 GitHub Pages

**라이브**: https://siadaddy.github.io/youngs/

- `ai-crew/main.py` 완료 시 자동 push
- 수동 push: `git add docs/ && git commit -m "..." && git push origin main`

### ⚠️ GitHub Actions 동시 push 주의
`newsletter` job과 `aicrew` job이 같은 브랜치에 순차 push함.  
로컬에서 수동 push 전 반드시 `git pull --rebase origin main` 먼저 실행.  
(aicrew workflow도 `git pull --rebase origin main` 후 push — 2026-06-03 적용)

### ⚠️ 콘텐츠 수동 추가 시 주의
오늘 날짜 카드를 수동으로 추가할 때는 **두 파일 모두 수정**해야 함:
1. `docs/content.json` ← 오늘 날짜 페이지가 이 파일에서 captions 로드
2. `docs/content/YYYY-MM-DD.json` ← 과거 날짜 조회용

`content/YYYY-MM-DD.json`만 수정하면 오늘 페이지에 반영 안 됨.

### 📰 뉴스 카테고리 (newsletter 수집)
- `🚘 BMW` — CARD 01 자동차 카드로 우선 선별 (planner.py `_CAR_KW` 등록)
- `🏢 삼천리 그룹` — 사업전략·실적·신사업 뉴스 시 5장 중 하나 강제 포함 (planner.py 규칙)
- 골프 협찬·단순 행사 등은 삼천리 규칙 제외 대상

### 🗣 오늘의 이야깃거리 (talking_points)
- TOP3 트렌드 브리핑과 **별도 풀**에서 생성 — TOP3 주제 재사용 금지
- `generate_talking_points()`에 TOP3 목록을 exclusion list로 전달, 가벼운/생활/스포츠 화제 우선
- 트렌드 브리핑(🔥 Today's Trend Briefing)과 내용 중복 방지 목적 (2026-06-03 수정)

---

## 🔍 빠른 상태 확인

```bash
# AI 크루 로그
tail -50 ai-crew/crew.log

# 오늘 콘텐츠 확인
ls docs/content/ | tail -5

# 카드 품질 로그 (최근 3일 재생성 현황)
python3 -c "
import json; d=json.load(open('ai-crew/quality_log.json'))
for r in d['runs'][-3:]:
    failed=[c for c in r['cards'] if not c.get('passed',True)]
    print(r['date'], f'{len(failed)}/{len(r[\"cards\"])}장 재생성', [c[\"issues\"] for c in failed])
"

# office_memory 직원 상태
python3 -c "import json; d=json.load(open('docs/office_memory.json')); [print(k, d['agents'][k].get('status','active')) for k in d['agents']]"

# Supabase agent_memories 동기화 테스트
cd ai-crew && python3 -c "from utils.agent_memory import _load_from_supabase; d=_load_from_supabase(); print(list(d.keys()))"
```

---

## 🎵 뮤직 유니버스 (docs/music.html)

Three.js 은하계 + MediaPipe 손 인식 컨트롤.

| 제스처 | 동작 |
|--------|------|
| ☝️ 검지 | 커서 이동 + 호버 |
| 🤏 엄지+검지 꽉 모음 | 클릭 → 재생 |
| 👌 엄지+검지 벌리기/모으기 | 줌인/아웃 |
| ✊ 주먹+이동 | 은하 회전 |
| 🖐 스와이프 | 이전/다음 곡 |

**주요 함수 (window._disco)**  
`setMouse(cx,cy)` · `doClick(cx,cy)` · `rotateGalaxy(dx,dy)` · `zoomGalaxy(delta)` · `playNext()` · `playPrev()`

---

## 🪙 코인 트레이더 (운용 종료)

| 항목 | 값 |
|------|-----|
| 운용 기간 | 2026-03 ~ 2026-05-25 |
| 총 거래 | 103회 |
| 최종 승률 | 33% |
| 누적 손익 | **-46,877원** |

> launchd 등록 해제됨. 파일(`../coin-trader/`)은 참조용으로 보존.
