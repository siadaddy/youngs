# youngs

> 시아아빠님의 AI 자동화 프로젝트 모음 — 서버 없이, 비용 없이, 맥북 하나로 돌아갑니다.

**라이브 사이트**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)

---

## 📦 프로젝트 목록

| 프로젝트 | 설명 | 실행 주기 |
|---------|------|---------|
| 📰 뉴스 수집 | RSS 피드 → 8개 카테고리 자동 분류 | 매일 06:40 |
| 🤖 AI 크리에이터 | 카드뉴스 5개 + 블로그 + 이미지 5장 + 음악 75곡 → GitHub Pages | 매일 07:00 |
| 🪙 AI 코인 자동매매 | 빗썸 KRW 마켓 AI 트레이딩 + GitHub Pages 대시보드 | 5분마다 |
| 🎓 내 제작물 | 저가 커피 입점 분석 + Instacart 대시보드 | 상시 배포 |

---

## 📰 뉴스 수집 + 🤖 AI 크리에이터

RSS 피드로 뉴스를 수집하고, 5명의 AI 직원이 협업해 콘텐츠를 자동 생성합니다.

- **첫 번째 카드뉴스**: 반드시 자동차/BMW/전기차 관련
- **source_facts 기반**: 원문에 없는 수치·사실 창작 금지
- **품질 5단계 후처리**: 블랙리스트 → 제목-본문 일관성 → 문장 품질 → 해시태그 위치 → 해시태그 수
- **이미지 실패 시** fallback 이미지 자동 대체 (None 노출 없음)

### 자동화 흐름

```
06:40 KST  📰 뉴스 수집 (com.siadad.newsletter)
               newsletter_naver.py — RSS 8개 카테고리
               → YYYY-MM-DD.md + YYYY-MM-DD_data.json

07:00 KST  🤖 AI 크리에이터 (com.siadad.aicrew)
           │
           ├─ 뉴스 데이터 확인 (없으면 긴급 수집 폴백)
           ├─ 🎯 기획자  — 뉴스 5개 선정, source_facts 생성
           ├─ ✍️  작가   — 카드뉴스 5개 + 블로그 아티클
           ├─ 🎨 디자이너 — Pollinations.ai 이미지 5장 (768×768)
           ├─ 🎵 음악 큐레이터 — 오늘의 음악 75곡 큐레이션
           └─ 📤 퍼블리셔 — GitHub Pages 자동 push

~07:20 KST  ✅ 완료 — 📱 ntfy 아이폰 알림
```

### AI 직원 소개

| 직원 | 역할 |
|------|------|
| 🎯 박기획 | 뉴스 5개 선정 (경제/산업/기술/국제 최소 3개), 지자체·소규모홍보 제외 |
| ✍️ 이작가 | 카드뉴스 5개 + 블로그 아티클, 5단계 품질 검사 |
| 🎨 최디자 | Pollinations.ai Flux 이미지 5장, 실패 시 fallback 자동 대체 |
| 🎵 한뮤직 | K-pop 20·인디팝 20·팝 20·R&B 15·기타 5곡, 발라드 20% 이하 |
| 📤 정퍼블 | GitHub Pages 자동 배포 (content.json, archive.json, images/) |

### 기술 스택

| 기술 | 용도 | 비용 |
|------|------|------|
| RSS feedparser | 뉴스 수집 (연합뉴스·YTN·MBC·SBS·한경·전자신문·헤럴드) | 무료 |
| Groq Llama 3.3 70B | 텍스트 생성 전반 (키 4개 라운드로빈) | 무료 |
| Pollinations.ai Flux | AI 이미지 생성 768×768 | 무료 |
| YouTube API + iTunes | 음악 검색·앨범아트 | 무료 |
| Three.js (WebGL) | 3D 뮤직 유니버스 | 무료 |
| GitHub Pages | 콘텐츠 호스팅 + 대시보드 | 무료 |
| ntfy.sh | 완료 알림 | 무료 |

---

## 🪙 AI 코인 자동매매

빗썸 KRW 마켓 거래대금 상위 20개 종목을 분석하고 Groq AI가 매매를 자동 실행합니다.

**라이브 대시보드**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/) → 코인 트레이더 탭

### 매매 흐름

```
매 5분 (하루 288회)
│
├─ Daily Drawdown 체크 → 일일 손실 한도 도달 시 당일 봇 정지
├─ 손절(-4%) / 익절(+6%) 체크 → 발동 시 즉시 매도 후 BUY 재탐색
├─ 빗썸 KRW 거래대금 상위 20개 선별
├─ 30분봉 RSI·MACD·볼린저밴드·ADX·변동성돌파 계산 (병렬 5개)
├─ 스코어링 → 상위 15개 Groq AI에 전달
├─ AI 오판 차단 필터 (실제 수익률 확인)
├─ 빗썸 시장가 주문 실행
├─ SELL 완료 → 즉시 매수 기회 재탐색 (현금 공백 최소화)
└─ docs/trades.json → GitHub Pages push (체결 시만)

상시  price_guard.py — 30초마다 현재가 감시 → 손절/익절 즉시 발동
```

### 기술 지표

| 지표 | 설정 | 매수 | 매도 |
|------|------|------|------|
| RSI | 14봉 (30분봉) | <35: +2 / <45: +1 | >65: -1 / >75: -2 |
| MACD | 12/26/9 | 골든크로스: +2 / 상승: +1 | 데드크로스: -2 / 하락: -1 |
| 볼린저밴드 | 20/2σ | 하단: +2 / 중하단: +1 | 상단: -2 / 중상단: -1 |
| ADX | 14봉 | ≥15 추세 있음 (매수 허용) | <15 횡보 (매수 금지) |
| **변동성 돌파** | K=0.5 (일봉) | **+2 보너스 (최우선 신호)** | — |

### 안전장치

| 기능 | 기준 |
|------|------|
| 손절 | 매수가 대비 -4% 자동 매도 |
| 익절 | 매수가 대비 +6% 자동 매도 |
| Daily Drawdown | 일일 누적 손실 -15,000원 초과 시 당일 봇 정지 |
| 3중 감시 | price_guard(30초) + main.py(5분) + AI 오판 차단 필터 |
| IP 변경 감지 | 공인 IP 변경 시 ntfy 긴급 알림 (빗썸 API 재등록 안내) |
| Groq 폴백 | 429 즉시 key1→2→3→4 전환 |
| DRY_RUN | 실제 주문 없이 전체 흐름 시뮬레이션 |
| 타임아웃 | 10분 초과 시 강제 종료 |

---

## 🎓 내 제작물 (패스트캠퍼스 INNER CIRCLE 2기)

### ☕ 저가 테이크아웃 커피 브랜드 입점 최적지 분석 (2025.05)
서울 유동인구·상권·임대료 데이터로 메가커피·컴포즈 최적 입점 후보지 도출 + Folium 지도 시각화

**라이브**: [siadaddy.github.io/youngs/map.html](https://siadaddy.github.io/youngs/map.html)

### 🛒 Instacart VIP 분석 대시보드 (2025.07)
인스타카트 구매 데이터로 VIP 고객 분류 + 맞춤 상품 추천 인터랙티브 대시보드

**배포**: [youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app](https://youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app)

---

## 🗂 저장소 구조

```
/Users/youngchulyu/ (git root)
│
├── README.md
├── docs/                       ← GitHub Pages
│   ├── index.html              ← 메인 대시보드 (뉴스레터·코인·뮤직 탭)
│   ├── music.html              ← 뮤직 유니버스 (Three.js 3D)
│   ├── about.html              ← AI 직원 소개
│   ├── content.json            ← 오늘 최신 콘텐츠
│   ├── archive.json            ← 날짜별 아카이브 (최대 60일)
│   ├── music.json              ← 오늘의 음악 목록
│   ├── trades.json             ← 코인 매매 이력 (최근 50건)
│   ├── content/                ← 날짜별 콘텐츠 JSON
│   └── images/                 ← AI 생성 이미지 영구 저장
│
├── app.py                      ← Instacart 대시보드 (Streamlit)
├── requirements.txt
│
└── 바이브코딩/
    ├── 뉴스레터/               ← newsletter_naver.py (RSS 수집)
    ├── ai-crew/                ← AI 크리에이터 파이프라인
    └── coin-trader/
        ├── main.py             ← 5분 AI 분석 (BUY/SELL/HOLD)
        └── price_guard.py      ← 30초 실시간 손절/익절 감시
```

---

## ⚙️ launchd 자동화 스케줄

| 에이전트 | 역할 | 실행 시간 |
|---------|------|---------|
| com.siadad.newsletter | RSS 뉴스 수집 | 매일 06:40 |
| com.siadad.aicrew | AI 크리에이터 전체 파이프라인 | 매일 07:00 |
| com.siadad.cointrader | AI 코인 매매 (5분 간격) | 매 :00/:05/…/:55 |
| com.siadad.coinreport | 일일 수익 리포트 | 매일 08:30 |
| com.siadad.coinip | IP 변경 감지 | 4시간마다 |
| com.siadad.priceguard | 30초 실시간 손절/익절 감시 | 상시 (KeepAlive) |

```bash
# 전체 상태 확인
launchctl list | grep siadad

# 개별 재시작 (예: aicrew)
launchctl unload ~/Library/LaunchAgents/com.siadad.aicrew.plist
launchctl load  ~/Library/LaunchAgents/com.siadad.aicrew.plist
```

---

## 📝 변경 이력

### 2026-04-12
- **뉴스 수집 분리**: 06:40 별도 LaunchAgent → ai-crew 07:00 즉시 시작 (~5분 단축)
- **Groq 키 4개**: ai-crew 라운드로빈 / coin-trader 폴백 체인
- **빗썸 전환 완료**: 업비트 → 빗썸 (pybithumb), 5분 간격 288회/일
- **AI 크리에이터 품질 5단계**: 해시태그 위치·수 검증 추가
- **음악 큐레이터 장르 균형**: K-pop 20 / 인디팝 20 / 팝 20 / R&B 15 / 기타 5, 발라드 20% 제한
- **이미지 fallback**: 생성 실패 시 fallback.png 자동 대체
- **기획자 강화**: 지자체·소규모 홍보 제외, 경제/기술/국제 최소 3개 강제

### 2026-04-11
- **5분 간격 전환**: 15분 → 5분 (96회/일 → 288회/일)
- **30분봉 전환**: 10분봉 → 30분봉, 익절 +6%, 손절 -4%
- **Daily Drawdown 보호**: 일일 손실 -15,000원 초과 시 당일 봇 정지
- **뮤직 유니버스**: music.html 탭 신규 추가 (Three.js 3D 은하)
- **작가 품질 3단계 후처리**: 블랙리스트 → 제목-본문 불일치 → 문장 품질

### 2026-04-06
- **빗썸 전환**: 업비트 → 빗썸 (pybithumb API 1.0)
- **SELL 후 즉시 BUY 재탐색**: 매도 완료 후 같은 사이클 내 매수 기회 탐색
- **AI 오판 차단 필터**: 실제 수익률 양수인데 AI가 손절 지시 시 HOLD 강제 전환

### 2026-04-03
- **작가 페르소나**: "시아아빠" (40대 BMW 딜러 직원) 도입
- **변동성 돌파(VB) 전략**: K=0.5, 최우선 매수 신호

### 2026-03-31
- **뉴스 수집 방식 변경**: 네이버 뉴스 API → RSS feedparser
- **GitHub Pages 단독 배포**: 노션 발행 중단

### 2026-03-27
- **로컬 자동화 전환**: GitHub Actions → macOS launchd
- **price_guard.py 추가**: 30초 실시간 손절/익절 감시 데몬

---

*최종 업데이트: 2026-04-12 | Powered by Groq + Pollinations.ai + pybithumb + Three.js + GitHub Pages*
