# 📰 뉴스레터 자동화 시스템

네이버 뉴스 검색 API로 매일 오전 8시 뉴스를 수집해 노션에 자동 업로드합니다.

---

## 구조

```
뉴스레터/
├── newsletter_naver.py   ← 메인 스크립트 (이걸 실행)
├── .env                  ← API 키 (숨김 파일, Cmd+Shift+. 로 표시)
├── newsletter.log        ← crontab 실행 로그
├── README.md             ← 이 파일
└── YYYY-MM-DD.md         ← 날짜별 수집 결과
```

---

## 설정 정보

| 항목 | 내용 |
|------|------|
| 실행 시간 | 매일 06:55 맥북 자동 깨움 → 07:00 launchd 실행 |
| 수집 방식 | 네이버 뉴스 검색 API |
| 노션 부모 페이지 | 뉴스레터 (329b395f9fc68169b2e8e7d06a621019) |
| 스크립트 | newsletter_naver.py |
| 로그 | newsletter.log |

### .env 파일 내용

```
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
GROQ_API_KEY=...
GROQ_API_KEY_2=...
NEWSLETTER_DIR=/Users/youngchulyu/바이브코딩/뉴스레터
```

### launchd 등록 (run_daily.sh → ai-crew가 통합 실행)

```bash
# 상태 확인
launchctl list | grep aicrew

# 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.aicrew.plist
launchctl load ~/Library/LaunchAgents/com.siadad.aicrew.plist
```

---

## 수집 카테고리

| 카테고리 | 키워드 |
|----------|--------|
| 🔥 오늘의 하이라이트 | 속보, 단독, 오늘 주요뉴스 |
| 🤖 AI / 인공지능 | AI 인공지능, ChatGPT, 생성형 AI, LLM |
| 💻 기술 / IT | 반도체 기술, 빅테크, IT 기업, 스타트업 |
| 💰 경제 / 금융 | 코스피 증시, 경제 금융, 부동산, 환율 금리 |
| 🚨 재난 / 안전 | 재난 안전, 자연재해, 소방 구조 |
| 🏙️ 사회 | 사회 이슈, 정치 뉴스, 복지 정책 |
| 🚗 자동차 | 전기차, 현대차 기아, 자율주행 |
| 🚘 BMW | BMW 뉴스, BMW 신차 |

---

## 수동 실행

```bash
cd /Users/youngchulyu/바이브코딩/뉴스레터
python3 newsletter_naver.py
```

---

## 네이버 API 키 재발급

1. https://developers.naver.com 접속
2. Application 등록 → 사용 API: **검색** 체크
3. Client ID / Client Secret 복사 → `.env` 에 붙여넣기

---

## 노션 문서

상세 가이드 & Jupyter Notebook용 코드:
https://www.notion.so/32bb395f9fc681c68eadc831b1d9be0b
