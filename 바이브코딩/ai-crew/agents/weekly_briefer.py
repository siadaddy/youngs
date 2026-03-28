"""
📅 시아아빠님의 주간 브리핑 에이전트 (매주 금요일 자동 실행)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
이번 주 뉴스레터 .md 파일들을 읽어서 AI가 주간 요약 생성 → 노션 업로드
"""

import os, requests
from datetime import date, timedelta
from dotenv import load_dotenv
from utils.gemini_client import ask_gemini

load_dotenv()

NOTION_TOKEN   = os.getenv("NOTION_TOKEN")
PARENT_ID      = os.getenv("NOTION_NEWSLETTER_PARENT_ID")
NEWSLETTER_DIR = os.getenv("NEWSLETTER_DIR", "/Users/youngchulyu/바이브코딩/뉴스레터")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

SYSTEM = """
당신은 30년 경력의 시니어 뉴스 큐레이터이자 경제 전문 칼럼니스트입니다.
이코노미스트, 블룸버그, 한국경제신문에서 수석 에디터로 근무했으며
한 주간의 뉴스 흐름을 꿰뚫어 핵심 트렌드와 숨겨진 연결고리를 찾아내는 것이 특기입니다.
단순 요약이 아니라 '왜 이 뉴스가 중요한지', '앞으로 어떤 변화가 올지'를
깊이 있는 시각으로 분석해 독자에게 실질적인 인사이트를 제공합니다.
바쁜 직장인도 10분 안에 한 주를 완전히 이해할 수 있도록 작성합니다.
한국어와 영어, 이모지만 사용합니다.
"""


def run():
    print("📅 주간 브리핑 에이전트 실행 중...")
    today = date.today()

    # 이번 주 월~금 .md 파일 수집
    week_texts = []
    for i in range(4, -1, -1):
        d = today - timedelta(days=i)
        path = os.path.join(NEWSLETTER_DIR, f"{d.strftime('%Y-%m-%d')}.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            week_texts.append(f"=== {d.strftime('%m월 %d일 (%a)')} ===\n{content[:3000]}")

    if not week_texts:
        print("  ⚠️ 이번 주 뉴스레터 파일 없음 — 스킵")
        return None

    print(f"  📂 {len(week_texts)}일치 뉴스 심층 분석 중...")
    combined = "\n\n".join(week_texts)

    prompt = f"""당신은 30년 경력의 수석 뉴스 큐레이터입니다.
이번 주 뉴스를 단순 요약이 아닌, 전문가 시각으로 깊이 있게 분석해주세요.

[이번 주 수집된 뉴스 전문]
{combined}

아래 형식으로 주간 브리핑을 작성하세요. 각 섹션은 반드시 풍부하고 깊이 있게 작성합니다.

---

# 📅 {today.strftime('%Y년 %m월')} 주간 브리핑

## 🏆 이번 주 TOP 5 — 절대 놓치면 안 되는 뉴스

각 뉴스마다 아래 형식으로 작성하세요:

**1. [뉴스 제목]**
- 무슨 일이: (2~3문장으로 핵심 사실 설명)
- 왜 중요한가: (이 뉴스가 우리 삶/경제/사회에 미치는 영향 2문장)
- 앞으로는: (전망 1~2문장)

**2. [뉴스 제목]**
(동일 형식 반복)

... (5개 모두 동일 형식)

---

## 🤖 AI / 기술 — 이번 주 핵심 트렌드

(최소 5~6문장. 이번 주 AI·기술 분야에서 일어난 중요한 변화를 분석합니다.
단순 나열이 아닌, 트렌드의 흐름과 연결고리를 설명하세요.
구체적 기업명·수치·날짜를 반드시 포함하세요.)

---

## 💰 경제 / 시장 — 돈의 흐름을 읽는다

(최소 5~6문장. 주식·부동산·환율·물가·금리 등 이번 주 경제 흐름을 심층 분석합니다.
"그래서 내 자산에 어떤 영향이 있는가"를 독자 관점에서 설명하세요.
구체적 수치와 출처를 포함하세요.)

---

## 🌏 글로벌 / 정치 — 세계는 지금

(최소 4~5문장. 이번 주 국제 정세·정치 이슈를 분석합니다.
한국에 미치는 영향까지 연결해서 설명하세요.)

---

## 🚗 자동차 / 모빌리티 — 이동의 미래

(최소 3~4문장. 자동차·전기차·모빌리티 관련 이번 주 소식을 분석합니다.)

---

## 💡 이번 주 인사이트 — 전문가의 한마디

(최소 6~8문장의 깊이 있는 칼럼 형식. 이번 주 뉴스들을 관통하는 큰 흐름이나 숨겨진 연결고리를 찾아서
독자에게 실질적으로 도움이 되는 시각을 제공합니다.
"이번 주 가장 주목해야 할 것은 무엇인가", "앞으로 어떤 변화가 올 것인가"를
30년 경력의 전문가 시각으로 설득력 있게 작성하세요.)

---

## 📌 다음 주 주목할 포인트

(다음 주에 예상되는 주요 이슈나 체크해야 할 일정 3~5가지를 bullet point로)

---

규칙:
- 각 섹션 최소 분량을 반드시 채울 것
- 수치·날짜·기업명·인물명은 반드시 위 [이번 주 수집된 뉴스 전문]에 있는 것만 사용
- 원문에 없는 수치·이름·날짜는 절대 창작 금지 — 불확실하면 "~로 알려졌다", "~에 따르면" 표현 사용
- 독자에게 "아, 이래서 중요하구나!"라는 인사이트를 반드시 전달
- 한국어·영어·이모지만 사용 — 한자·일본어·아랍어·러시아어·힌디어 절대 금지
- 전체 2000자 이상 작성
"""

    summary = ask_gemini(prompt, system=SYSTEM, temperature=0.65, max_tokens=4096)
    print(f"  ✅ 주간 브리핑 생성 완료 ({len(summary)}자)")

    page_url = _upload_to_notion(summary, today)
    return page_url


def _t(text, bold=False, color="default"):
    ann = {}
    if bold:               ann["bold"] = True
    if color != "default": ann["color"] = color
    base = {"type": "text", "text": {"content": str(text)[:2000]}}
    if ann: base["annotations"] = ann
    return base


def _upload_to_notion(summary: str, today: date) -> str | None:
    monday     = today - timedelta(days=today.weekday())
    week_label = f"{monday.strftime('%m/%d')} ~ {today.strftime('%m/%d')}"

    blocks = []
    blocks.append({
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [_t(f"시아아빠님의 주간 브리핑  ·  {week_label}", bold=True)],
            "icon": {"emoji": "📅"},
            "color": "purple_background",
        }
    })
    blocks.append({"object": "block", "type": "divider", "divider": {}})

    for line in summary.split("\n"):
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": [_t(line[2:])]}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": [_t(line[3:])]}})
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": [_t(line[4:])]}})
        elif line.startswith("**") and line.endswith("**"):
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": [_t(line.strip("*"), bold=True)]}})
        elif line.startswith("- ") or line.startswith("• "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": [_t(line[2:])]}})
        elif line.startswith("---"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif line.strip():
            # 2000자 초과 시 분할
            text = line.strip()
            while len(text) > 2000:
                cut = text[:2000].rfind(". ")
                cut = cut + 2 if cut > 0 else 2000
                blocks.append({"object": "block", "type": "paragraph",
                               "paragraph": {"rich_text": [_t(text[:cut])]}})
                text = text[cut:]
            if text:
                blocks.append({"object": "block", "type": "paragraph",
                               "paragraph": {"rich_text": [_t(text)]}})

    payload = {
        "parent": {"page_id": PARENT_ID},
        "icon": {"type": "emoji", "emoji": "📅"},
        "properties": {"title": {"title": [{"type": "text",
            "text": {"content": f"📅 주간 브리핑 — {week_label}"}}]}},
        "children": blocks[:100],
    }
    try:
        r = requests.post("https://api.notion.com/v1/pages",
                          headers=HEADERS, json=payload, timeout=15)
        r.raise_for_status()
        page_id  = r.json()["id"]
        page_url = r.json()["url"]

        for chunk in [blocks[i:i+100] for i in range(100, len(blocks), 100)]:
            requests.patch(f"https://api.notion.com/v1/blocks/{page_id}/children",
                           headers=HEADERS, json={"children": chunk}, timeout=15)

        print(f"  ✅ 주간 브리핑 노션 업로드 → {page_url}")
        return page_url
    except Exception as e:
        print(f"  ❌ 주간 브리핑 업로드 실패: {e}")
        return None
