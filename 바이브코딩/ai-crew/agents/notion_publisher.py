import os, requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
PARENT_ID    = os.getenv("NOTION_NEWSLETTER_PARENT_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def run(brief: dict, writer_output: dict, images: list, newsletter_data: dict = None) -> str:
    """항상 새 페이지 생성:
    상단 — AI 크리에이터 콘텐츠 (카드뉴스 + 블로그 아티클)
    하단 — 오늘 수집된 뉴스레터 원문
    """
    print("📤 노션 퍼블리셔 에이전트 실행 중...")
    today_str = date.today().strftime("%Y년 %m월 %d일")

    blocks = _build_blocks(brief, writer_output, images, newsletter_data)
    chunks = [blocks[i:i+100] for i in range(0, len(blocks), 100)]

    payload = {
        "parent": {"page_id": PARENT_ID},
        "icon": {"type": "emoji", "emoji": "🤖"},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": f"🤖 {today_str}"}}]}
        },
        "children": chunks[0],
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload, timeout=15)
    r.raise_for_status()
    page_id  = r.json()["id"]
    page_url = r.json()["url"]

    for chunk in chunks[1:]:
        requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=HEADERS, json={"children": chunk}, timeout=15,
        )

    print(f"  ✅ 노션 페이지 생성 완료 → {page_url}")
    return page_url


# ─────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────

def _t(text, bold=False, color="default"):
    ann = {}
    if bold:               ann["bold"] = True
    if color != "default": ann["color"] = color
    base = {"type": "text", "text": {"content": str(text)}}
    if ann: base["annotations"] = ann
    return base


def _para(text, bold=False, color="default"):
    return {
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [_t(text, bold=bold, color=color)]},
    }


def _divider():
    return {"object": "block", "type": "divider", "divider": {}}


def _split_text_blocks(text, block_type="paragraph"):
    """2000자 초과 텍스트를 문장 단위로 분할해 블록 리스트로 반환"""
    blocks = []
    while len(text) > 2000:
        cut = text[:2000].rfind(". ")
        cut = cut + 2 if cut > 0 else 2000
        blocks.append({
            "object": "block", "type": block_type,
            block_type: {"rich_text": [_t(text[:cut])]},
        })
        text = text[cut:]
    if text.strip():
        blocks.append({
            "object": "block", "type": block_type,
            block_type: {"rich_text": [_t(text)]},
        })
    return blocks


# ─────────────────────────────────────────────────────────────────
# 전체 블록 조립
# ─────────────────────────────────────────────────────────────────

def _build_blocks(brief, writer, images, newsletter_data):
    today_str = date.today().strftime("%Y년 %m월 %d일")
    blocks = []

    # ══ 메인 헤더 ════════════════════════════════════════════════
    blocks.append({
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [_t(f"🤖 시아아빠님의 AI 크리에이터  ·  {today_str}", bold=True)],
            "icon": {"emoji": "🤖"},
            "color": "blue_background",
        },
    })
    blocks.append(_divider())

    # ══ 섹션 1: 카드뉴스 (이미지 먼저, 글 아래) ══════════════════
    blocks.append({
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [_t("📰 오늘의 카드뉴스")]},
    })

    for i, item in enumerate(writer["captions"]):
        # 카드 번호 + 헤드라인
        blocks.append({
            "object": "block", "type": "heading_3",
            "heading_3": {"rich_text": [_t(f"#{i+1}  {item['headline']}")]},
        })

        # 이미지 — GitHub Pages URL이면 임베드, 아니면 링크
        if i < len(images):
            img = images[i]
            if img.get("url"):
                url = img["url"]
                if "github.io" in url:
                    # GitHub Pages URL → Notion에서 직접 로드 가능
                    blocks.append({
                        "object": "block", "type": "image",
                        "image": {"type": "external", "external": {"url": url}},
                    })
                else:
                    # Pollinations URL → 링크로 대체
                    blocks.append({
                        "object": "block", "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                _t("🖼 AI 생성 이미지: ", color="gray"),
                                {
                                    "type": "text",
                                    "text": {"content": "웹사이트에서 보기", "link": {"url": "https://siadaddy.github.io/youngs/"}},
                                    "annotations": {"color": "blue", "underline": True},
                                },
                            ]
                        },
                    })

        # 카드뉴스 글 (이미지 아래)
        caption = item["caption"]
        for para in caption.split("\n"):
            if not para.strip():
                continue
            blocks.extend(_split_text_blocks(para.strip()))

        if i < len(writer["captions"]) - 1:
            blocks.append(_divider())

    blocks.append(_divider())

    # ══ 섹션 2: 블로그 아티클 ════════════════════════════════════
    blocks.append({
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [_t("🧠 AI 에디터 PICK")]},
    })

    article = writer["article"]
    for line in article.split("\n"):
        if line.startswith("## "):
            blocks.append({
                "object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [_t(line[3:])]},
            })
        elif line.startswith("# "):
            blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [_t(line[2:])]},
            })
        elif line.startswith("- "):
            text = line[2:]
            blocks.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [_t(text[:2000])]},
            })
        elif line.strip():
            blocks.extend(_split_text_blocks(line.strip()))

    blocks.append(_divider())
    blocks.append(_para(
        f"자동 생성: {date.today().strftime('%Y-%m-%d')}  ·  Powered by Groq (Llama 3.3) + Stable Horde",
        color="gray",
    ))

    # ══ 섹션 3: 오늘 수집된 뉴스레터 원문 (하단) ════════════════
    if newsletter_data:
        blocks.append(_divider())
        blocks.append(_divider())
        blocks.append({
            "object": "block", "type": "callout",
            "callout": {
                "rich_text": [_t(
                    f"📰 오늘 수집된 뉴스  ·  수집 시각: {newsletter_data.get('collected_at', today_str)}",
                    bold=True,
                )],
                "icon": {"emoji": "📰"},
                "color": "gray_background",
            },
        })

        # AI 요약 (dict 또는 str 모두 처리)
        ai_summary = newsletter_data.get("ai_summary", "")
        if ai_summary:
            blocks.append({
                "object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [_t("🏆 AI 선정 오늘의 TOP 3")]},
            })
            if isinstance(ai_summary, dict):
                for item in ai_summary.get("top3", []):
                    rank  = item.get("rank", "")
                    title = item.get("title", "")
                    why   = item.get("why", "")
                    cat   = item.get("category", "")
                    line  = f"{rank}위  {title}" + (f"  [{cat}]" if cat else "")
                    blocks.append({
                        "object": "block", "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": [_t(line[:2000], bold=True)]},
                    })
                    if why:
                        blocks.extend(_split_text_blocks(f"  └ {why[:500]}"))
            else:
                for para in str(ai_summary).split("\n"):
                    if not para.strip():
                        continue
                    blocks.extend(_split_text_blocks(para.strip()))

        # 카테고리별 뉴스 목록
        categorized = newsletter_data.get("categorized", {})
        for cat, articles in categorized.items():
            if not articles:
                continue
            blocks.append({
                "object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [_t(f"📌 {cat}")]},
            })
            for art in articles:
                title   = art.get("title", "")
                source  = art.get("source", "")
                link    = art.get("link", "")
                summary = art.get("summary", "")

                rich = []
                # 출처 레이블 (볼드, 회색)
                if source:
                    rich.append(_t(f"[{source}]  ", bold=True, color="gray"))
                # 제목 (링크 포함)
                title_block = {
                    "type": "text",
                    "text": {"content": title[:1800], "link": {"url": link} if link else None},
                    "annotations": {"bold": True},
                }
                rich.append(title_block)

                blocks.append({
                    "object": "block", "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": rich},
                })
                if summary:
                    blocks.extend(_split_text_blocks(f"  └ {summary[:500]}"))

    return blocks
