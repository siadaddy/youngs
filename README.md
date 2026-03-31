# youngs

> 시아아빠님의 AI 자동화 프로젝트 모음 — 서버 없이, 비용 없이, 맥북 하나로 돌아갑니다.

**라이브 사이트**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)

---

## 📦 프로젝트 목록

| 프로젝트 | 설명 | 실행 주기 |
|----------|------|-----------|
| [📰 뉴스레터 + AI 크리에이터](#-뉴스레터--ai-크리에이터) | 뉴스 수집 → 카드뉴스 5개 + 블로그 아티클 + 이미지 → 노션 | 매일 07:00 |
| [🤖 AI 코인 자동매매](#-ai-코인-자동매매) | 업비트 KRW 마켓 AI 자동 트레이딩 + GitHub Pages 대시보드 | 하루 6회 (4시간) |
| [🎓 내 제작물 (INNER CIRCLE 2기)](#-내-제작물-패스트캠퍼스-inner-circle-2기) | 저가 커피 입점 분석 (2025.05) + Instacart 대시보드 (2025.07) | 상시 배포 |

---

## 📰 뉴스레터 + AI 크리에이터

네이버 뉴스 API로 매일 8개 카테고리 뉴스를 수집하고, 5명의 AI 직원이 협업해 콘텐츠를 자동 생성합니다. (카드뉴스 5개 + 블로그 1개 + AI 이미지 5장)
- 자동차 뉴스 1개 필수 포함, 나머지 4개는 AI가 주요 뉴스 선정
- 카드뉴스마다 원문 출처 링크 포함
- Stable Horde 계정 API 키로 이미지 생성 안정성 확보

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
| 🎯 박기획 | 핵심 뉴스 5개 선정 (자동차 필수 1개 + 4개), 원문 URL 포함 source_facts 브리프 |
| ✍️ 이작가 | 카드뉴스 5개 + 블로그 아티클 (Groq 키 라운드로빈 분배, 카드 간 5초 대기) |
| 🎨 최디자 | 768×768 AI 이미지 5장 (Stable Horde Flux.1-Schnell, 밝고 모던한 스타일) |
| 📤 정퍼블 | 노션 업로드 (AI 콘텐츠 상단 / 수집 뉴스 카테고리 토글 하단) |
| 📅 한주간 | 금요일 주간 브리핑 자동 생성 |

### 기술 스택

| 기술 | 용도 | 비용 |
|------|------|------|
| Naver News API | 8개 카테고리 뉴스 수집 | 무료 |
| Groq (Llama 3.3 70B) | 텍스트 생성 전반 (키2개 라운드로빈 분배) | 무료 |
| Stable Horde Flux.1-Schnell | AI 이미지 생성 768×768 (계정 키, ~20초) | 무료 |
| Notion API | 콘텐츠 저장 (수집 뉴스 토글 형태) | 무료 |
| GitHub Pages | 이미지 호스팅 + 사이트 (수집 뉴스 토글 포함) | 무료 |
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
│    ├─ -7% 이하 → 🔴 자동 손절 매도
│    └─ +15% 이상 → 🟡 자동 익절 매도
├─ Step 3: 업비트 KRW 마켓 거래량 상위 20개 선별
├─ Step 4: 4시간봉 RSI / MACD / 볼린저밴드 / ADX 계산
├─ Step 5: Groq AI → BUY / SELL / HOLD 판단 + 한국어 이유
├─ Step 6: 업비트 시장가 주문 실행
├─ Step 7: state.json 저장
├─ Step 8: ntfy 결과 알림
└─ Step 9: docs/trades.json 업데이트 → GitHub Pages push

08:30 KST  📊 일일 리포트 (com.siadad.coinreport)
           어제 손익 / 누적 손익 / 승률 / 총 거래 횟수 → ntfy 알림
```

### 기술 지표 (스코어링 방식)

| 지표 | 설정 | 매수 신호 | 매도 신호 |
|------|------|-----------|-----------|
| RSI | 14 | 35~40 이하 (+1~+2점) | 65~75 이상 (-1~-2점) |
| MACD | 12/26/9 | 골든크로스 (+2점) / 상승 (+1점) | 데드크로스 (-2점) / 하락 (-1점) |
| 볼린저밴드 | 20/2 | 하단 (+2점) / 중하단 (+1점) | 상단 (-2점) / 중상단 (-1점) |
| ADX | 14 | **20 이상 필수** (추세 확인) | 20 미만이면 매수 금지 |

**매수**: 합산 +4점 이상 + ADX 20 이상 | **매도**: -2점 이하 or 손절/익절 도달
**기회 교체**: 보유 종목 횡보(-3%~+3%) + 다른 종목 +4점 이상 → SELL 후 교체

### 안전장치

| 기능 | 기준 |
|------|------|
| 손절 | 매수가 대비 -7% 자동 매도 |
| 익절 | 매수가 대비 +15% 자동 매도 |
| IP 사전 점검 | 거래 1시간 전 현재 IP ntfy 알림 (23:05 / 03:05 / 07:05 / 11:05 / 15:05 / 19:05) |
| IP 변경 감지 | 변경 시 ntfy 긴급 알림 + 업비트 재등록 안내 |
| 실행 타임아웃 | 10분 초과 시 강제 종료 (네트워크 hang 방지) |
| Groq 라운드로빈 | 키2개 번갈아 사용 → TPM 2배 확보, 429 시 즉시 전환 |
| DRY_RUN | 실제 주문 없이 전체 흐름 시뮬레이션 |

**상세 문서**: [바이브코딩/coin-trader/README.md](바이브코딩/coin-trader/README.md)

---

## 🎓 내 제작물 (패스트캠퍼스 INNER CIRCLE 2기)

패스트캠퍼스 이너서클 2기 팀 프로젝트로 제작한 데이터 분석 결과물입니다.

### ☕ 저가 테이크아웃 커피 브랜드 입점 최적지 분석 (2025.05)

서울열린데이터광장 유동인구·상권·임대료 데이터를 기반으로 메가커피·컴포즈 등 저가 커피 브랜드의 서울 내 최적 입점 후보지를 도출하고 Folium으로 지도 시각화한 발표 프로젝트.

- **라이브**: [siadaddy.github.io/youngs/map.html](https://siadaddy.github.io/youngs/map.html)
- **데이터**: 서울열린데이터광장 (유동인구, 상권, 임대료)
- **기술**: Python, Folium, 입지 분석

### 🛒 Instacart VIP 분석 대시보드 (2025.07)

인스타카트 구매 데이터를 분석해 VIP 고객을 분류하고 맞춤 상품을 추천하는 인터랙티브 대시보드.

- **배포**: [youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app](https://youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app/)
- **DB**: Google Drive → gdown으로 `/tmp/`에 자동 다운로드 (DuckDB)
- **기술**: Python, Streamlit, DuckDB

---

## 🗂 저장소 구조

```
/Users/youngchulyu/ (git root)
│
├── README.md
├── docs/                       ← GitHub Pages
│   ├── index.html              ← 메인 (탭 UI: 코인 트레이더 기본 / AI 뉴스레터)
│   ├── about.html              ← AI 직원 소개 & 파이프라인 & 기술 스택
│   ├── content.json            ← 오늘 최신 콘텐츠
│   ├── archive.json            ← 날짜 목록 (최대 60일)
│   ├── trades.json             ← 코인 매매 이력 (최근 50건)
│   ├── map.html                ← 저가 커피 입점 최적지 지도 시각화
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
         ├── main.py            ← 4시간 AI 분석 (BUY/SELL/HOLD)
         └── price_guard.py     ← 30초 실시간 손절/익절 감시 데몬
```

---

## ⚙️ launchd 관리

| 에이전트 | 역할 | 실행 시간 |
|----------|------|-----------|
| com.siadad.aicrew | 뉴스레터 + AI 크리에이터 | 매일 07:00 |
| com.siadad.cointrader | AI 코인 자동매매 | 00:05 / 04:05 / 08:05 / 12:05 / 16:05 / 20:05 |
| com.siadad.coinreport | 일일 수익 리포트 | 매일 08:30 |
| com.siadad.coinip | 거래 1시간 전 IP 점검 | 23:05 / 03:05 / 07:05 / 11:05 / 15:05 / 19:05 |
| com.siadad.priceguard | 30초 실시간 손절/익절 감시 | 상시 실행 (KeepAlive) |

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

# IP 점검 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.coinip.plist
launchctl load ~/Library/LaunchAgents/com.siadad.coinip.plist

# 가격 감시 재시작
launchctl unload ~/Library/LaunchAgents/com.siadad.priceguard.plist
launchctl load ~/Library/LaunchAgents/com.siadad.priceguard.plist
```

---

*최종 업데이트: 2026-03-31 (2차) | Powered by Groq + Stable Horde Flux.1-Schnell + pyupbit + Notion API + GitHub Pages*

---

## 📝 변경 이력

### 2026-03-31
- **AI 크리에이터**: 카드뉴스 5개 복구 (자동차 필수 1개 + AI 선정 4개)
- **AI 크리에이터**: 카드뉴스마다 원문 출처 링크 버튼 추가 (노션 + GitHub Pages)
- **AI 크리에이터**: Stable Horde 계정 API 키 적용 — 익명 키 403 오류 해결
- **AI 크리에이터**: 이미지 스타일 변경 — 어두운 다큐 → 밝고 모던한 Bloomberg/Wired 스타일
- **AI 크리에이터**: Groq 키 라운드로빈 분배 — 카드 간 대기 20초 → 5초 단축
- **AI 크리에이터**: 원문 뉴스 URL planner에 전달 → source_url 브리프에 포함
- **GitHub Pages**: 뉴스레터 탭 하단 수집 뉴스 카테고리별 토글 추가 (8개 카테고리 × 5건)
- **노션**: 수집 뉴스 카테고리별 토글 형태로 변경
- **제작물**: 패스트캠퍼스 INNER CIRCLE 2기 배지 + 제작 날짜 추가
- **제작물**: 저가 테이크아웃 커피 입점 최적지 분석 (지도 시각화) 추가
- **코인 트레이더**: 코인 섹션 헤더 개선 — "AI가 5천원으로 코인을 직접 삽니다"

### 2026-03-30
- **코인 트레이더**: 30초 실시간 가격 감시 데몬 추가 (price_guard.py, KeepAlive)
- **코인 트레이더**: 손절/익절 즉시 실행 — 기존 4시간 대기 → 30초 이내 대응
- **GitHub Pages**: 탭 UI 추가 — 코인 트레이더(기본) / AI 뉴스레터 탭 분리
- **GitHub Pages**: 코인 대시보드 실시간 현재가 표시 (업비트 API 직접 호출, 30초 갱신)
- **GitHub Pages**: 티커테이프 KOSPI/삼성전자(미지원) → WTI원유/이더리움으로 교체
- **AI 크리에이터**: 이미지 생성 모델 교체 — 구 ICBINP(만료) → Stable Horde Flux.1-Schnell (약 20초, 무료)

### 2026-03-29
- **코인 트레이더**: 퀀트 연구 기반 트레이딩 규칙 전면 업그레이드
  - ADX 지표 추가 — 추세 없는 횡보장 진입 차단 (승률 +15% 효과)
  - 스코어링 방식 도입 — RSI·MACD·BB 합산 점수 기반 BUY/SELL 판단
  - RSI 매수 기준 30 → 35~40, 매도 기준 70 → 65~70
  - 손절 -5% → -7%, 익절 +10% → +15% (알트코인 4시간봉 변동폭 반영)
  - 기회 교체 조건 개선 — 거래량 기준 +100% → +50%, RSI 30 → 40
- **코인 트레이더**: 거래 1시간 전 IP 사전 점검 ntfy 알림 추가 (com.siadad.coinip)
- **코인 트레이더**: 10분 실행 타임아웃 추가 + TimeoutError ntfy 알림
- **코인 트레이더**: 손절/익절 주문 실패 시 예외 처리 + ntfy 긴급 알림
- **코인 트레이더**: check_exit 네트워크 오류 시 프로그램 중단 방지
- **코인 트레이더**: 예상치 못한 오류 전체 catch → ntfy 알림 (조용히 죽는 케이스 제거)
- **GitHub Pages**: 카드뉴스 3개로 축소, AI 직원·파이프라인·기술 스택 → about.html 분리
- **AI 크리에이터**: planner 카드뉴스 5개 → 3개로 변경

### 2026-03-28
- **코인 트레이더**: 실행 시각 정각 → 4시간봉 마감 5분 후 (`:05`)로 변경
- **코인 트레이더**: 익절 +10% 자동 매도 추가 (기존 손절 -5%만 있었음)
- **코인 트레이더**: 일일 수익 리포트 추가 (매일 08:30 ntfy 알림)
- **GitHub Pages**: 히어로 섹션 코인 트레이더 내용 추가, "AI 자동화 허브"로 타이틀 변경
- **GitHub Pages**: 매매 히스토리 reason 텍스트 줄바꿈 허용 (CSS 수정)
