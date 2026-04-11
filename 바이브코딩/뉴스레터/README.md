# 📰 뉴스레터 자동화 시스템

> RSS 피드로 매일 오전 뉴스를 자동 수집해 카테고리별로 정리하는 시스템

**실행 환경**: MacBook (launchd) — 매일 07:00 자동 실행

---

## 구조

```
뉴스레터/
├── newsletter_rss.py    ← 메인 스크립트 (RSS 수집 + 카테고리 분류)
├── newsletter.py        ← 레거시 (미사용)
├── .env                 ← API 키 (숨김 파일, Cmd+Shift+. 로 표시)
├── newsletter.log       ← launchd 실행 로그
├── README.md            ← 이 파일
└── YYYY-MM-DD.md        ← 날짜별 수집 결과
```

---

## 설정 정보

| 항목 | 내용 |
|------|------|
| 실행 시간 | 매일 07:00 launchd 자동 실행 |
| 수집 방식 | RSS feedparser (공신력 있는 매체 직접 구독) |
| 출력 | `YYYY-MM-DD.md` + `YYYY-MM-DD_data.json` |
| 스크립트 | newsletter_rss.py |
| 로그 | newsletter.log |

### .env 파일 내용

```
GROQ_API_KEY=...
GROQ_API_KEY_2=...
NEWSLETTER_DIR=/Users/youngchulyu/바이브코딩/뉴스레터
```

### launchd 관리

```bash
# 상태 확인
launchctl list | grep aicrew

# 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.aicrew.plist
launchctl load ~/Library/LaunchAgents/com.siadad.aicrew.plist
```

---

## RSS 피드 소스

| 매체 | 피드 |
|------|------|
| 연합뉴스 | 뉴스 / 경제 / 사회 |
| YTN | 전체 기사 |
| MBC | 뉴스 |
| SBS | 뉴스 |
| 한국경제 | 전체 / 경제 / 산업 |
| 전자신문 | 전체 기사 |
| 헤럴드경제 | 비즈 |

---

## 수집 카테고리

| 카테고리 | 키워드 예시 |
|----------|------------|
| 🔥 오늘의 하이라이트 | 속보, 긴급, 단독, 대통령, 외교 |
| 🤖 AI / 인공지능 | AI, 인공지능, ChatGPT, LLM, GPT, 에이전트 |
| 💻 기술 / IT | 반도체, 클라우드, 블록체인, 해킹, IT기업 |
| 💰 경제 / 금융 | 코스피, 환율, 금리, 부동산, 투자, 증시 |
| 🚨 사건 / 사고 | 사고, 화재, 체포, 수사, 범죄, 폭발 |
| 🏙️ 사회 | 정치, 국회, 선거, 복지, 교육, 환경 |
| 🚗 자동차 | 전기차, 현대차, 자율주행, EV, 하이브리드 |
| 🚘 BMW | BMW, iX, i4, i5, M5, M3 |

---

## 수동 실행

```bash
cd /Users/youngchulyu/바이브코딩/뉴스레터
python3 newsletter_rss.py
```

---

## 설치

```bash
pip install feedparser requests python-dotenv
```

---

## 출력 예시

수집 완료 시 두 파일 생성:
- `2026-04-11.md` — 마크다운 뉴스레터 (GitHub Pages 뉴스레터 탭에 표시)
- `2026-04-11_data.json` — 카테고리별 구조화 데이터
