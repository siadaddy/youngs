#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
매일 아침 뉴스레터 자동 생성 스크립트
- 공신력 있는 매체에서 뉴스 수집
- Claude API로 요약 정리
- 마크다운 파일 저장 + 노션 업로드
"""

import os
import re
import time
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from ddgs import DDGS

# .env 파일 로드
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID")
NEWSLETTER_DIR = os.getenv("NEWSLETTER_DIR", str(Path(__file__).parent))

# 허용 매체
ALLOWED_SITES = [
    "yna.co.kr", "ytn.co.kr", "imnews.imbc.com",
    "news.sbs.co.kr", "hankyung.com", "mk.co.kr",
    "etnews.com", "biz.heraldcorp.com", "heraldcorp.com"
]

# 뉴스 카테고리
CATEGORIES = [
    {"name": "오늘의 하이라이트", "emoji": "🔥", "query": "오늘 주요뉴스 화제"},
    {"name": "AI / 인공지능",    "emoji": "🤖", "query": "AI 인공지능"},
    {"name": "기술 / IT",        "emoji": "💻", "query": "IT 기술 반도체"},
    {"name": "경제 / 금융",      "emoji": "💰", "query": "경제 금융 주식"},
    {"name": "사건 / 사고",      "emoji": "🚨", "query": "사건 사고"},
    {"name": "사회",             "emoji": "🏙️", "query": "사회 정책"},
    {"name": "자동차",           "emoji": "🚗", "query": "자동차 전기차"},
    {"name": "BMW",              "emoji": "🚘", "query": "BMW"},
]


def search_news(query: str, max_results: int = 5) -> list[dict]:
    """DuckDuckGo에서 허용 매체 기사만 검색"""
    site_query = " OR ".join([f"site:{s}" for s in ALLOWED_SITES])
    full_query = f"{query} ({site_query})"
    results = []

    try:
        with DDGS() as ddgs:
            for r in ddgs.news(full_query, max_results=max_results * 2):
                url = r.get("url", "")
                if any(site in url for site in ALLOWED_SITES):
                    source = r.get("source", "")
                    results.append({
                        "title": r.get("title", ""),
                        "url": url,
                        "body": r.get("body", "")[:200],
                        "source": source,
                    })
                if len(results) >= max_results:
                    break
    except Exception as e:
        print(f"  ⚠️  검색 오류 ({query}): {e}")

    return results


def collect_all_news() -> dict:
    """모든 카테고리 뉴스 수집"""
    all_news = {}
    for i, cat in enumerate(CATEGORIES):
        key = f"{cat['emoji']} {cat['name']}"
        print(f"  검색 중: {key}...")
        all_news[key] = search_news(cat["query"])
        if i < len(CATEGORIES) - 1:
            time.sleep(2)  # 요청 간 딜레이 (rate limit 방지)
    return all_news


def format_newsletter(all_news: dict, date_str: str) -> str:
    """뉴스 데이터를 마크다운 뉴스레터로 포맷팅 (API 불필요)"""
    today_kr = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y년 %m월 %d일")

    lines = [
        f"# 📰 뉴스레터 - {today_kr}",
        "",
        "> 출처: 연합뉴스, YTN, MBC, SBS, 한국경제, 전자신문, 헤럴드경제 등 공신력 있는 매체만",
        "",
        "---",
        "",
    ]

    for category, articles in all_news.items():
        lines.append(f"## {category}")
        if not articles:
            lines.append("- 수집된 기사 없음")
        else:
            for a in articles:
                title  = a.get("title", "").strip()
                url    = a.get("url", "").strip()
                body   = a.get("body", "").strip()
                source = a.get("source", "").strip()
                if not title or not url:
                    continue
                summary = f" — {body[:120]}" if body else ""
                lines.append(f"- **[{source}] [{title}]({url})**{summary}")
        lines.append("")

    lines += [
        "---",
        f"*수집 시각: {date_str} {datetime.now().strftime('%H:%M')}*",
    ]
    return "\n".join(lines)


def save_markdown(content: str, date_str: str) -> str:
    """마크다운 파일 저장"""
    filepath = os.path.join(NEWSLETTER_DIR, f"{date_str}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


# ── Notion 업로드 관련 함수들 ─────────────────────────────────────────────────

def parse_rich_text(text: str) -> list[dict]:
    """마크다운 텍스트를 Notion rich_text 블록으로 변환"""
    rich_text = []
    pattern = r'\*?\*?\[([^\]]+)\]\(([^)]+)\)\*?\*?'
    last_end = 0

    for match in re.finditer(pattern, text):
        before = re.sub(r'\*\*', '', text[last_end:match.start()])
        if before.strip():
            rich_text.append({"type": "text", "text": {"content": before}})

        rich_text.append({
            "type": "text",
            "text": {"content": match.group(1), "link": {"url": match.group(2)}},
            "annotations": {"bold": True},
        })
        last_end = match.end()

    remaining = re.sub(r'\*\*', '', text[last_end:])
    if remaining.strip():
        rich_text.append({"type": "text", "text": {"content": remaining}})

    return rich_text or [{"type": "text", "text": {"content": text[:2000]}}]


def markdown_to_notion_blocks(md: str) -> list[dict]:
    """마크다운을 Notion 블록 리스트로 변환"""
    blocks = []
    for line in md.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                            "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                            "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:]}}]}})
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                            "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:]}}]}})
        elif line.startswith("- "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                            "bulleted_list_item": {"rich_text": parse_rich_text(line[2:])}})
        elif line.startswith("---"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif line.startswith("> "):
            blocks.append({"object": "block", "type": "quote",
                            "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}})
        elif line.startswith("*") and line.endswith("*"):
            blocks.append({"object": "block", "type": "paragraph",
                            "paragraph": {"rich_text": [{"type": "text", "text": {"content": line.strip("*")},
                                                         "annotations": {"italic": True}}]}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                            "paragraph": {"rich_text": [{"type": "text", "text": {"content": line[:2000]}}]}})
    return blocks


def upload_to_notion(content: str, date_str: str):
    """Notion에 뉴스레터 하위 페이지 생성"""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    today_kr = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y년 %m월 %d일")

    # 페이지 생성
    page_data = {
        "parent": {"page_id": NOTION_PARENT_PAGE_ID},
        "icon": {"type": "emoji", "emoji": "📰"},
        "properties": {
            "title": {"title": [{"text": {"content": f"📰 {today_kr} 뉴스레터"}}]}
        },
    }
    res = requests.post("https://api.notion.com/v1/pages", headers=headers, json=page_data)
    page = res.json()
    if "id" not in page:
        print(f"  ⚠️  노션 페이지 생성 실패: {page.get('message', '')}")
        return

    page_id = page["id"]

    # 블록 추가 (100개씩 배치)
    blocks = markdown_to_notion_blocks(content)
    for i in range(0, len(blocks), 100):
        batch = blocks[i:i + 100]
        requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=headers,
            json={"children": batch},
        )

    print(f"  ✅ 노션 업로드 완료: {page.get('url', '')}")


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n📰 뉴스레터 생성 시작 — {today}")
    print("=" * 50)

    print("\n[1/4] 뉴스 수집 중...")
    all_news = collect_all_news()

    print("\n[2/4] 뉴스레터 포맷팅 중...")
    newsletter = format_newsletter(all_news, today)

    print("\n[3/4] 마크다운 파일 저장 중...")
    filepath = save_markdown(newsletter, today)
    print(f"  ✅ 저장 완료: {filepath}")

    print("\n[4/4] 노션 업로드 중...")
    upload_to_notion(newsletter, today)

    print("\n" + "=" * 50)
    print(f"✅ 완료! {today} 뉴스레터가 생성됐습니다.")


if __name__ == "__main__":
    main()
