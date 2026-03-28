# youngs

> 시아아빠님의 AI 자동화 프로젝트 모음

## 🤖 AI 크리에이터

매일 07:00 KST, AI가 뉴스를 읽고 SNS 카드뉴스 5개 + 블로그 아티클을 자동 생성합니다.

- **라이브 사이트**: [siadaddy.github.io/youngs](https://siadaddy.github.io/youngs/)
- **상세 문서**: [바이브코딩/ai-crew/README.md](바이브코딩/ai-crew/README.md)

### 파이프라인 구조
```
네이버 뉴스 API → 기획자 → 작가 → 디자이너 → 노션 + GitHub Pages
```

### 사용 기술 (전부 무료)
- **Groq** (Llama 3.3 70B) — 텍스트 생성
- **Stable Horde** — AI 이미지 생성
- **GitHub Pages** — 사이트 + 이미지 호스팅
- **Notion API** — 콘텐츠 저장

---

## 📊 Instacart 대시보드

Streamlit으로 만든 Instacart 데이터 분석 대시보드입니다.

- **배포**: [youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app](https://youngs-9ewwwhdidksu3qeifbh2qb.streamlit.app/)
- **DB**: Google Drive → gdown으로 `/tmp/`에 자동 다운로드 (DuckDB)
