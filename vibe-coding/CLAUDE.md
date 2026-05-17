# 시아아빠의 AI 데일리 — Claude Code 컨텍스트
> 마지막 업데이트: 2026-05-12

## 📦 프로젝트 구조

```
youngs/ (git root — siadaddy.github.io/youngs)
├── docs/                    ← GitHub Pages
│   ├── index.html           ← 메인 대시보드
│   ├── content.json / archive.json / music.json / weekly_trend.json
│   ├── office_memory.json   ← AI 직원 학습 기록 (ai-crew + coin-trader 병합)
│   ├── trades.json          ← 코인 매매 기록
│   └── images/              ← Pollinations.ai 생성 이미지 (30일 자동 정리)
├── ai-crew/                 ← AI 뉴스레터 (GitHub Actions 매일 07:00 KST)
├── newsletter/              ← 네이버 API 뉴스 수집 (GitHub Actions 매일 06:40 KST)
└── vibe-coding/
    └── coin-trader/         ← AI 코인 자동매매 (맥북 로컬 launchd, 30분마다)
```

> git root는 `youngs/` 폴더. `git add docs/index.html` 처럼 상대경로 사용.
> coin-trader는 맥북 로컬 전용 (GitHub Actions 미연결).

---

## ⚙️ 실행 구조

| 작업 | 방식 | 시간 |
|------|------|------|
| 뉴스 수집 (newsletter) | GitHub Actions | 매일 06:40 KST |
| AI 뉴스레터 (ai-crew) | GitHub Actions (needs: newsletter) | 매일 07:00 KST |
| 코인 매매 (main.py) | 맥북 launchd | 30분마다 |
| 손절/익절 감시 (price_guard.py) | 맥북 launchd | 상시 30초 루프 |
| 일일 리포트 | 맥북 launchd | 08:30 |

---

## 🗄 Supabase 테이블

| 테이블 | 내용 |
|--------|------|
| `news_trends` | 날짜별 TOP3 + category_summaries |
| `news_cards` | 카드뉴스 본문 데이터 |
| `agent_memories` | AI 직원 학습 데이터 (agent_name PK, events jsonb, diary jsonb, persona, growth_score) |

---

## 🔑 API 키 & LLM 전략

- **ai-crew** (`ai-crew/.env`): Gemini 2.5-flash 우선 → Groq 폴백
- **coin-trader** (`vibe-coding/coin-trader/.env`): Groq 우선 → Gemini 폴백

---

## 🪙 코인 트레이더 설정 (2026-05-04 기준)

| 항목 | 값 |
|------|-----|
| 투자금 | 5만원 |
| 손절 | -4% |
| 익절 | +5% |
| 트레일링스탑 | +2.5% 활성 / -2.0% 트리거 |
| 강제청산 | 6시간 |
| 일일손실한도 | -7,500원 |
| 쿨다운 | 종목 6h / 전역 4h |

**학습 블랙리스트**: 손절 1회→6h쿨, 2회→3일, 3회→7일, 4회→14일, 5회+→30일

---

## 📚 핵심 파일

| 파일 | 역할 |
|------|------|
| `ai-crew/utils/agent_memory.py` | Supabase agent_memories 연동 |
| `ai-crew/utils/office_export.py` | ai-crew 4명 학습 기록 → office_memory.json |
| `ai-crew/agents/designer.py` | Pollinations.ai 이미지 생성 (30일 자동 정리) |
| `ai-crew/agents/weekly_trend.py` | 주간 트렌드 (매주 월요일) |
| `vibe-coding/coin-trader/main.py` | 코인 오케스트레이터 |
| `vibe-coding/coin-trader/price_guard.py` | 손절/익절 30초 감시 |
| `vibe-coding/coin-trader/utils/blacklist.py` | 학습 블랙리스트 |
| `vibe-coding/coin-trader/utils/office_export.py` | AI어드바이저 기록 → office_memory.json |

---

## 🔍 빠른 상태 확인

```bash
# 코인 보유 현황
cat vibe-coding/coin-trader/state.json

# 코인 로그
tail -50 vibe-coding/coin-trader/trader.log

# AI 크루 로그
tail -50 ai-crew/crew.log

# 블랙리스트 현황
cd vibe-coding/coin-trader && python3 -c "from utils.blacklist import get_summary; [print(l) for l in get_summary()]"
```

---

## 🎭 AI 사무실 (index.html)

Canvas 픽셀아트 AI 직원 8명 + CSS 아이소메트릭 배경 + 낮/밤 자동전환.  
`office_memory.json` 실데이터 연동, 30초 자동 갱신.

| 직원 | 역할 | 데이터 출처 |
|------|------|------------|
| 박기획 | 콘텐츠 기획자 | agent_memories (Supabase) |
| 최디자 | 이미지 디자이너 | agent_memories (Supabase) |
| 한뮤직 | 음악 큐레이터 | agent_memories (Supabase) |
| AI주간트렌드 | 주간 분석가 | agent_memories (Supabase) |
| AI어드바이저 | 코인 어드바이저 | coin-trader/utils/office_export.py (로컬) |
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
