# 시아아빠의 AI 데일리 — Claude Code 컨텍스트
> 마지막 업데이트: 2026-05-18

## 📦 프로젝트 구조

```
/Users/youngchulyu/vibe-coding/   ← 작업 루트
├── coin-trader/                  ← AI 코인 자동매매 (맥북 로컬 launchd, 4시간마다)
└── youngs/                       ← git repo (siadaddy.github.io/youngs)
    ├── docs/                     ← GitHub Pages
    │   ├── index.html            ← 메인 대시보드
    │   ├── content/              ← 날짜별 카드뉴스 JSON (2026-MM-DD.json)
    │   ├── images/               ← Pollinations.ai 생성 이미지 (30일 자동 정리)
    │   ├── office_memory.json    ← AI 직원 학습 기록 (ai-crew + coin-trader 병합)
    │   ├── trades.json           ← 코인 매매 기록
    │   └── supabase-client.js    ← Supabase 연동 (news_trends, news_cards)
    ├── ai-crew/                  ← AI 뉴스레터 (GitHub Actions 매일 07:00 KST)
    └── newsletter/               ← 네이버 API 뉴스 수집 (GitHub Actions 매일 06:40 KST)
```

> `youngs/`가 git root. Claude Code 작업 시 `git add docs/index.html` 처럼 youngs/ 기준 상대경로 사용.  
> coin-trader는 youngs/ 밖 (`../coin-trader/`). 별도 git repo(상위 `~/`)에서 추적됨.

---

## ⚙️ 실행 구조

| 작업 | 방식 | 시간 |
|------|------|------|
| 뉴스 수집 (newsletter) | GitHub Actions | 매일 06:40 KST |
| AI 뉴스레터 (ai-crew) | GitHub Actions (needs: newsletter) | 매일 07:00 KST |
| 코인 매매 (main.py) | 맥북 launchd | **4시간마다** |
| 손절/익절 감시 (price_guard.py) | 맥북 launchd | 상시 30초 루프 |
| 일일 리포트 | 맥북 launchd | 08:30 |

---

## 🗄 Supabase 테이블

| 테이블 | 내용 |
|--------|------|
| `news_trends` | 날짜별 TOP3 + category_summaries + **talking_points** (오늘의 이야깃거리) |
| `news_cards` | 카드뉴스 본문 데이터 |
| `agent_memories` | AI 직원 학습 데이터 (ai-crew 4명 + coin-trader 어드바이저) — agent_name PK, data JSONB |

> `news_trends.talking_points`는 `newsletter_naver.py`가 생성·저장. index.html '오늘의 이야깃거리' 섹션에서 표시.  
> `agent_memories`는 `ai-crew/utils/agent_memory.py`와 `coin-trader/utils/agent_memory.py` 양쪽에서 `_save()` 호출 시 자동 upsert.

---

## 🔑 API 키 & LLM 전략

- **ai-crew** (`ai-crew/.env`): Gemini 2.5-flash 우선 → Groq 폴백
- **coin-trader** (`../coin-trader/.env`): Groq 우선 → Gemini 폴백 (GROQ_KEY 4개 순환)

---

## 🪙 코인 트레이더 설정 (2026-05-18 기준)

| 항목 | 값 |
|------|-----|
| 투자금 | 5만원 |
| 손절 | **-2.5%** |
| 익절 | **+6.0%** |
| 트레일링스탑 | **+2.0% 활성 / -1.5% 트리거** |
| 강제청산 | **4시간** |
| 일일손실한도 | -7,500원 |
| 쿨다운 | 종목 6h / 전역 4h |

**손익비**: 2.4 (break-even 승률 29.4% → 실제 34%면 수익)  
**학습 블랙리스트**: 손절 1회→6h쿨, 2회→3일, 3회→7일, 4회→14일, 5회+→30일  
**매수 조건**: RSI 28~65 + ADX 28+ + 점수 +6 이상 (불충족 시 LLM 호출 없이 즉시 HOLD)

---

## 📚 핵심 파일

| 파일 | 역할 |
|------|------|
| `newsletter/newsletter_naver.py` | 뉴스 수집 + AI 요약 + **오늘의 이야깃거리** 생성 → Supabase |
| `ai-crew/utils/agent_memory.py` | ai-crew 4명 메모리 → Supabase agent_memories 동기화 |
| `ai-crew/utils/office_export.py` | ai-crew 학습 기록 → office_memory.json |
| `ai-crew/agents/designer.py` | Pollinations.ai 이미지 생성 (30일 자동 정리) |
| `ai-crew/agents/weekly_trend.py` | 주간 트렌드 (매주 월요일) — json_mode=False, max_tokens 4096 |
| `../coin-trader/main.py` | 코인 오케스트레이터 |
| `../coin-trader/price_guard.py` | 손절/익절 30초 감시 |
| `../coin-trader/agents/ai_advisor.py` | LLM 매매 판단 + 자기반성 일기 (100자, 종목·지표 직접 언급) |
| `../coin-trader/utils/agent_memory.py` | 코인봇 메모리 → Supabase agent_memories 동기화 |
| `../coin-trader/utils/blacklist.py` | 학습 블랙리스트 |

---

## 🔍 빠른 상태 확인

```bash
# 코인 보유 현황
cat ../coin-trader/state.json

# 코인 로그
tail -50 ../coin-trader/trader.log

# AI 크루 로그
tail -50 ai-crew/crew.log

# 블랙리스트 현황
cd ../coin-trader && python3 -c "from utils.blacklist import get_summary; [print(l) for l in get_summary()]"

# launchd 코인봇 상태 확인
launchctl list | grep trader
# '-  0  com.siadad.cointrader' → 정상 (마지막 종료 코드 0)
```

---

## 🎭 AI 사무실 (index.html)

Canvas 픽셀아트 AI 직원 8명 + CSS 아이소메트릭 배경 + 낮/밤 자동전환.  
`office_memory.json` 실데이터 연동, 30초 자동 갱신.

| 직원 | 역할 | 데이터 출처 |
|------|------|------------|
| 박기획 | 콘텐츠 기획자 | Supabase agent_memories |
| 최디자 | 이미지 디자이너 | Supabase agent_memories |
| 한뮤직 | 음악 큐레이터 | Supabase agent_memories |
| AI주간트렌드 | 주간 분석가 | Supabase agent_memories |
| AI어드바이저 | 코인 어드바이저 | Supabase agent_memories |
| 뉴스기자 / 이가드 / 리포터 | 보조 직원 | 표시 전용 |

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
| 🤲 양손 | 큰 폭 줌 |

**주요 함수 (window._disco)**
- `setMouse(cx, cy)` — 호버 위치 업데이트
- `doClick(cx, cy)` — 직접 레이캐스팅 후 재생
- `rotateGalaxy(dx, dy)` — galaxyGroup 회전
- `zoomGalaxy(delta)` — camera ↔ controls.target 거리 조정
- `playNext()` / `playPrev()`

---

## 🌐 GitHub Pages

**라이브**: https://siadaddy.github.io/youngs/

- `ai-crew/main.py` 완료 시 자동 push
- `coin-trader/main.py` 매매 체결 시 자동 push
