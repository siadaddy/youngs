# youngs

> 시아아빠님의 AI 자동화 프로젝트 모음 — 서버 없이, 비용 없이, 맥북 하나로 돌아갑니다.

**라이브 사이트**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)

---

## 📦 프로젝트 목록

| 프로젝트 | 설명 | 실행 주기 |
|----------|------|-----------|
| [📰 뉴스레터 + AI 크리에이터](#-뉴스레터--ai-크리에이터) | 뉴스 수집 → 카드뉴스 5개 + 블로그 아티클 + 이미지 → 노션 | 매일 07:00 |
| [🤖 AI 코인 자동매매](#-ai-코인-자동매매) | 업비트 KRW 마켓 AI 자동 트레이딩 + GitHub Pages 대시보드 | 하루 6회 (4시간) |
| [📊 Instacart 대시보드](#-instacart-대시보드) | Streamlit + DuckDB 데이터 분석 앱 | 상시 배포 |

---

## 📰 뉴스레터 + AI 크리에이터

네이버 뉴스 API로 매일 8개 카테고리 뉴스를 수집하고, 5명의 AI 직원이 협업해 콘텐츠를 자동 생성합니다.

### 자동화 흐름

```
07:00 KST  launchd (com.siadad.aicrew)
           │
           ├─ Step 1: 뉴스레터 수집 (newsletter_naver.py)
           │    네이버 뉴스 API → 8개 카테고리 → Groq AI 요약 + TOP 3 선정
           │    → .md / _data.json 로컬 저장
           │
           └─ Step 2: AI 크리에이터 (main.py)
                🎯 기획자 → ✍️ 작가 → 🎨 디자이너 → 📤 노션 퍼블리셔
                → docs/images/ 저장 → GitHub Pages 자동 push
                → 금요일: 📅 주간 브리퍼 자동 추가
                각 단계 실패 시 최대 3회 자동 재시도 (10초 간격)

~08:00 KST  ✅ 완료 — 📱 ntfy 앱으로 아이폰 알림
```

### AI 직원 소개

| 직원 | 역할 |
|------|------|
| 🎯 박기획 | 핵심 뉴스 5개 선정, source_facts 기반 콘텐츠 브리프 |
| ✍️ 이작가 | 카드뉴스 5개 + 블로그 아티클 (temperature 0.7, 원문 사실 기반) |
| 🎨 최디자 | 768×768 AI 이미지 5장 (Stable Horde 무료) |
| 📤 정퍼블 | 노션 페이지 업로드 (AI 콘텐츠 상단 / 수집 뉴스 하단) |
| 📅 한주간 | 금요일 주간 브리핑 자동 생성 |

### 기술 스택

| 기술 | 용도 | 비용 |
|------|------|------|
| Naver News API | 8개 카테고리 뉴스 수집 | 무료 |
| Groq (Llama 3.3 70B) | 텍스트 생성 전반 (key1→key2 폴백) | 무료 |
| Stable Horde | AI 이미지 생성 768×768 | 무료 |
| Notion API | 콘텐츠 저장 | 무료 |
| GitHub Pages | 이미지 영구 호스팅 + 사이트 | 무료 |
| ntfy.sh | 완료 알림 | 무료 |

**상세 문서**: [바이브코딩/ai-crew/README.md](바이브코딩/ai-crew/README.md)

---

## 🤖 AI 코인 자동매매

업비트 KRW 마켓에서 AI가 하루 6회 종목을 분석하고 자동으로 매수/매도합니다.

**라이브 대시보드**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/) → 코인 트레이더 탭

### 매매 흐름

```
00:05 / 04:05 / 08:05 / 12:05 / 16:05 / 20:05 (launchd, 4시간봉 마감 5분 후)
│
├─ Step 0: 공인 IP 변경 감지 (변경 시 ntfy 긴급 알림)
├─ Step 1: 보유 상태 로드 (state.json)
├─ Step 2: 손절/익절 체크 (보유 중일 때)
│    ├─ -5% 이하 → 🔴 자동 손절 매도
│    └─ +10% 이상 → 🟡 자동 익절 매도
├─ Step 3: 업비트 KRW 마켓 거래량 상위 20개 선별
├─ Step 4: 4시간봉 RSI / MACD / 볼린저밴드 계산
├─ Step 5: Groq AI → BUY / SELL / HOLD 판단 + 한국어 이유
├─ Step 6: 업비트 시장가 주문 실행
├─ Step 7: state.json 저장
├─ Step 8: ntfy 결과 알림
└─ Step 9: docs/trades.json 업데이트 → GitHub Pages push

08:30 KST  📊 일일 리포트 (com.siadad.coinreport)
           어제 손익 / 누적 손익 / 승률 / 총 거래 횟수 → ntfy 알림
```

### 기술 지표

| 지표 | 설정 | 매수 | 매도 |
|------|------|------|------|
| RSI | 14 | 30 이하 (과매도) | 70 이상 (과매수) |
| MACD | 12/26/9 | 골든크로스 | 데드크로스 |
| 볼린저밴드 | 20/2 | 하단 근접 | 상단 근접 |

### 안전장치

| 기능 | 기준 |
|------|------|
| 손절 | 매수가 대비 -5% 자동 매도 |
| 익절 | 매수가 대비 +10% 자동 매도 |
| IP 변경 감지 | ntfy 긴급 알림 + 업비트 재등록 안내 |
| Groq 폴백 | key1 소진 시 key2 자동 전환 |
| DRY_RUN | 실제 주문 없이 전체 흐름 시뮬레이션 |

**상세 문서**: [바이브코딩/coin-trader/README.md](바이브코딩/coin-trader/README.md)

---

## 📊 Instacart 대시보드

Streamlit + DuckDB로 만든 Instacart 데이터 분석 대시보드입니다.

- **배포**: [youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app](https://youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app/)
- **DB**: Google Drive → gdown으로 `/tmp/`에 자동 다운로드 (DuckDB)

---

## 🗂 저장소 구조

```
/Users/youngchulyu/ (git root)
│
├── README.md
├── docs/                       ← GitHub Pages
│   ├── index.html              ← 라이브 사이트 (AI 크리에이터 + 코인 대시보드)
│   ├── content.json            ← 오늘 최신 콘텐츠
│   ├── archive.json            ← 날짜 목록 (최대 60일)
│   ├── trades.json             ← 코인 매매 이력 (최근 50건)
│   ├── content/                ← 날짜별 콘텐츠 아카이브
│   └── images/                 ← AI 생성 이미지 영구 저장
│
├── app.py                      ← Instacart 대시보드 (Streamlit)
├── requirements.txt
│
└── 바이브코딩/
    ├── 뉴스레터/               ← 뉴스 수집 (newsletter_naver.py)
    ├── ai-crew/                ← AI 크리에이터 파이프라인
    └── coin-trader/            ← AI 코인 자동매매
```

---

## ⚙️ launchd 관리

| 에이전트 | 역할 | 실행 시간 |
|----------|------|-----------|
| com.siadad.aicrew | 뉴스레터 + AI 크리에이터 | 매일 07:00 |
| com.siadad.cointrader | AI 코인 자동매매 | 00:05 / 04:05 / 08:05 / 12:05 / 16:05 / 20:05 |
| com.siadad.coinreport | 일일 수익 리포트 | 매일 08:30 |

```bash
# 상태 확인
launchctl list | grep siadad

# ai-crew 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.aicrew.plist
launchctl load ~/Library/LaunchAgents/com.siadad.aicrew.plist

# 코인 트레이더 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.cointrader.plist
launchctl load ~/Library/LaunchAgents/com.siadad.cointrader.plist

# 일일 리포트 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.coinreport.plist
launchctl load ~/Library/LaunchAgents/com.siadad.coinreport.plist
```

---

*최종 업데이트: 2026-03-28 | Powered by Groq + Stable Horde + pyupbit + Notion API + GitHub Pages*

---

## 📝 변경 이력

### 2026-03-28
- **코인 트레이더**: 실행 시각 정각 → 4시간봉 마감 5분 후 (`:05`)로 변경
- **코인 트레이더**: 익절 +10% 자동 매도 추가 (기존 손절 -5%만 있었음)
- **코인 트레이더**: 일일 수익 리포트 추가 (매일 08:30 ntfy 알림)
- **GitHub Pages**: 히어로 섹션 코인 트레이더 내용 추가, "AI 자동화 허브"로 타이틀 변경
- **GitHub Pages**: 매매 히스토리 reason 텍스트 줄바꿈 허용 (CSS 수정)
