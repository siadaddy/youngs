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

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PARENT_ID    = os.getenv("NOTION_NEWSLETTER_PARENT_ID")
NEWSLETTER_DIR = os.getenv("NEWSLETTER_DIR",
                           "/Users/youngchulyu/바이브코딩/뉴스레터")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

SYSTEM = """
당신은 주간 뉴스 큐레이터입니다.
한 주 동안의 뉴스를 핵심만 간결하게 요약하여 바쁜 직장인이 5분 안에 읽을 수 있도록 작성합니다.
"""

def run():
    print("📅 주간 브리핑 에이전트 실행 중...")
    today = date.today()

    # 이번 주 월~금 .md 파일 수집
    week_texts = []
    for i in range(4, -1, -1):  # 금요일부터 5일 전까지
        d = today - timedelta(days=i)
        path = os.path.join(NEWSLETTER_DIR, f"{d.strftime('%Y-%m-%d')}.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            week_texts.append(f"=== {d.strftime('%m월 %d일')} ===\n{content[:2000]}")

    if not week_texts:
        print("  ⚠️ 이번 주 뉴스레터 파일 없음 — 스킵")
        return None

    print(f"  📂 {len(week_texts)}일치 뉴스 분석 중...")
    combined = "\n\n".join(week_texts)

    prompt = f"""이번 주({today.strftime('%Y년 %m월')} 주간) 뉴스를 분석하고 아래 형식으로 주간 브리핑을 작성해주세요.

[이번 주 뉴스 모음]
{combined}

작성 형식:
# 📅 이번 주 핵심 뉴스 요약

## 🏆 이번 주 TOP 5 뉴스
(가장 중요한 5개 뉴스, 한 줄씩 핵심만)

## 🤖 AI / 기술 동향
(2~3문장 요약)

## 💰 경제 / 시장 흐름
(2~3문장 요약)

## 🚗 자동차 / BMW 소식
(2~3문장 요약)

## 💡 이번 주 인사이트
(한 주를 돌아보는 한 단락, 독자에게 가치 있는 시각 제공)
"""

    summary = ask_gemini(prompt, system=SYSTEM, temperature=0.6)
    print("  ✅ 주간 요약 생성 완료")

    page_url = _upload_to_notion(summary, today)
    return page_url


def _t(text, bold=False, color="default"):
    ann = {}
    if bold:               ann["bold"] = True
    if color != "default": ann["color"] = color
    base = {"type": "text", "text": {"content": str(text)}}
    if ann: base["annotations"] = ann
    return base


def _upload_to_notion(summary: str, today: date) -> str | None:
    # 주간 날짜 범위 계산 (월~금)
    monday = today - timedelta(days=today.weekday())
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

    # 마크다운 요약을 Notion 블록으로 변환
    for line in summary.split("\n"):
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": [_t(line[2:])]}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": [_t(line[3:])]}})
        elif line.startswith("- ") or line.startswith("• "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": [_t(line[2:])]}})
        elif line.strip():
            for k in range(0, len(line), 500):
                blocks.append({"object": "block", "type": "paragraph",
                               "paragraph": {"rich_text": [_t(line[k:k+500])]}})

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
