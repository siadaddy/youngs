#!/usr/bin/env python3
"""
📰 뉴스레터 자동 수집기 (RSS 기반 — Claude API 불필요)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
실행 방법:
  pip install feedparser requests python-dotenv
  python3 newsletter_rss.py

필요 환경변수 (.env 파일):
  NOTION_TOKEN=ntn_xxxxx
  NOTION_PARENT_PAGE_ID=329b395f-9fc6-8169-b2e8-e7d06a621019
  NEWSLETTER_DIR=/Users/youngchulyu/바이브코딩/뉴스레터
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os, re, time, requests
from datetime import datetime, date
from dotenv import load_dotenv

try:
    import feedparser
except ImportError:
    print('feedparser 없음 → pip install feedparser')
    exit(1)

load_dotenv()

# ── 설정 ───────────────────────────────────────────────
NOTION_TOKEN     = os.getenv('NOTION_TOKEN', '')
NOTION_PARENT_ID = os.getenv('NOTION_PARENT_PAGE_ID', '329b395f-9fc6-8169-b2e8-e7d06a621019')
NEWSLETTER_DIR   = os.getenv('NEWSLETTER_DIR', os.path.dirname(os.path.abspath(__file__)))
TODAY            = date.today().strftime('%Y-%m-%d')
MAX_PER_CATEGORY = 5

# ── RSS 피드 (공신력 있는 매체만) ─────────────────────────
RSS_FEEDS = {
    '연합뉴스': [
        'https://www.yna.co.kr/rss/news.xml',
        'https://www.yna.co.kr/rss/economy.xml',
        'https://www.yna.co.kr/rss/society.xml',
    ],
    'YTN': [
        'https://www.ytn.co.kr/rss/allArticleRss.php',
    ],
    'MBC': [
        'https://imnews.imbc.com/rss/news/news_00.xml',
    ],
    'SBS': [
        'https://news.sbs.co.kr/news/rss/noticeSectionList.do?sectionId=01',
    ],
    '한국경제': [
        'https://www.hankyung.com/feed/all-news',
        'https://www.hankyung.com/feed/economy',
        'https://www.hankyung.com/feed/industry',
    ],
    '전자신문': [
        'https://www.etnews.com/rss/allArticleRss.xml',
    ],
    '헤럴드경제': [
        'https://biz.heraldcorp.com/rss',
    ],
}

# ── 카테고리 키워드 ────────────────────────────────────
CATEGORIES = {
    '🔥 오늘의 하이라이트': [
        '속보', '긴급', '주요뉴스', '단독', '발표', '선언', '대통령', '총리', '외교'
    ],
    '🤖 AI / 인공지능': [
        'AI', '인공지능', '머신러닝', '딥러닝', 'ChatGPT', '생성형AI', 'LLM',
        '챗봇', '클로드', '제미나이', 'GPT', '에이전트'
    ],
    '💻 기술 / IT': [
        '반도체', '스마트폰', '앱', '플랫폼', '클라우드', '소프트웨어',
        '디지털', '메타버스', '블록체인', '사이버', '해킹', 'IT기업'
    ],
    '💰 경제 / 금융': [
        '주식', '코스피', '코스닥', '환율', '금리', '부동산', '경제성장',
        '금융', '증시', '달러', '인플레이션', '무역', '수출', '수입', '투자'
    ],
    '🚨 사건 / 사고': [
        '사고', '화재', '사망', '부상', '체포', '구속', '수사', '사건',
        '범죄', '피해', '충돌', '폭발', '붕괴', '실종'
    ],
    '🏙️ 사회': [
        '정치', '정부', '법원', '국회', '선거', '복지', '교육', '의료',
        '보건', '환경', '기후', '여성', '청년', '인구'
    ],
    '🚗 자동차': [
        '자동차', '전기차', '현대차', '기아', '자율주행', '배터리',
        '신차', '출시', '리콜', '모빌리티', 'EV', '하이브리드'
    ],
    '🚘 BMW': [
        'BMW', '비엠더블유', 'iX', 'i4', 'i5', 'i7', 'iX3',
        'M5', 'M3', 'Neue Klasse'
    ],
}

# ── RSS 수집 ────────────────────────────────────────────
def fetch_all_articles():
    all_articles = []
    seen_links = set()

    for source, urls in RSS_FEEDS.items():
        count = 0
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:20]:
                    link    = entry.get('link', '').strip()
                    title   = entry.get('title', '').strip()
                    summary = re.sub(r'<[^>]+>', '', entry.get('summary', '')).strip()[:300]

                    if not title or not link or link in seen_links:
                        continue
                    seen_links.add(link)
                    all_articles.append({
                        'source':  source,
                        'title':   title,
                        'link':    link,
                        'summary': summary,
                    })
                    count += 1
                time.sleep(0.3)
            except Exception as e:
                print(f'    ⚠️  {source} ({url}) 실패: {e}')
        print(f'    {source}: {count}개')

    return all_articles

# ── 카테고리 분류 ────────────────────────────────────────
def categorize(articles):
    result = {cat: [] for cat in CATEGORIES}
    used = set()

    for cat, keywords in CATEGORIES.items():
        for art in articles:
            if id(art) in used:
                continue
            text = (art['title'] + ' ' + art['summary']).lower()
            if any(kw.lower() in text for kw in keywords):
                result[cat].append(art)
                used.add(id(art))
                if len(result[cat]) >= MAX_PER_CATEGORY:
                    break

    return result

# ── 마크다운 생성 ────────────────────────────────────────
def build_markdown(categorized):
    today_str = date.today().strftime('%Y년 %m월 %d일')
    now_str   = datetime.now().strftime('%Y-%m-%d %H:%M')

    lines = [
        f'# 📰 뉴스레터 - {today_str}',
        '',
        '> 출처: 연합뉴스, YTN, MBC, SBS, 한국경제, 전자신문, 헤럴드경제',
        '',
        '---',
        '',
    ]

    for cat, articles in categorized.items():
        lines.append(f'## {cat}')
        if not articles:
            lines.append('- 수집된 기사 없음')
        else:
            for a in articles:
                desc = f' — {a["summary"]}' if a['summary'] else ''
                lines.append(f'- **[{a["source"]}] [{a["title"]}]({a["link"]})**{desc}')
        lines.append('')

    lines += ['---', f'*수집 시각: {now_str}*', '']
    return '\n'.join(lines)

# ── 파일 저장 ────────────────────────────────────────────
def save_markdown(content):
    os.makedirs(NEWSLETTER_DIR, exist_ok=True)
    path = os.path.join(NEWSLETTER_DIR, f'{TODAY}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'    저장 완료: {path}')
    return path

# ── Notion 업로드 ────────────────────────────────────────
def build_notion_blocks(categorized):
    """카테고리별 Notion 블록 생성"""
    blocks = []

    # 안내 callout
    blocks.append({
        'object': 'block', 'type': 'callout',
        'callout': {
            'rich_text': [{'type': 'text', 'text': {'content':
                '출처: 연합뉴스, YTN, MBC, SBS, 한국경제, 전자신문, 헤럴드경제'}}],
            'icon': {'emoji': '📡'}
        }
    })
    blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})

    for cat, articles in categorized.items():
        # 섹션 제목
        blocks.append({
            'object': 'block', 'type': 'heading_2',
            'heading_2': {'rich_text': [{'type': 'text', 'text': {'content': cat}}]}
        })

        if not articles:
            blocks.append({
                'object': 'block', 'type': 'paragraph',
                'paragraph': {'rich_text': [{'type': 'text',
                    'text': {'content': '수집된 기사 없음'},
                    'annotations': {'color': 'gray'}}]}
            })
        else:
            for a in articles:
                desc = f'  {a["summary"][:100]}' if a['summary'] else ''
                blocks.append({
                    'object': 'block', 'type': 'bulleted_list_item',
                    'bulleted_list_item': {
                        'rich_text': [
                            {'type': 'text',
                             'text': {'content': f'[{a["source"]}] ', },
                             'annotations': {'bold': True, 'color': 'blue'}},
                            {'type': 'text',
                             'text': {'content': a['title'], 'link': {'url': a['link']}},
                             'annotations': {'bold': True}},
                            {'type': 'text',
                             'text': {'content': desc}},
                        ]
                    }
                })

    blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})
    blocks.append({
        'object': 'block', 'type': 'paragraph',
        'paragraph': {'rich_text': [{'type': 'text',
            'text': {'content': f'수집 시각: {datetime.now().strftime("%Y-%m-%d %H:%M")}'},
            'annotations': {'italic': True, 'color': 'gray'}}]}
    })

    return blocks

def upload_to_notion(categorized):
    if not NOTION_TOKEN:
        print('    ⚠️  NOTION_TOKEN 없음 → .env 파일 확인')
        return

    today_str = date.today().strftime('%Y년 %m월 %d일')
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28',
    }

    blocks = build_notion_blocks(categorized)
    # Notion API: 한 번에 최대 100 블록
    first_chunk  = blocks[:100]
    extra_chunks = [blocks[i:i+100] for i in range(100, len(blocks), 100)]

    payload = {
        'parent': {'page_id': NOTION_PARENT_ID},
        'icon': {'type': 'emoji', 'emoji': '📰'},
        'properties': {
            'title': {'title': [{'type': 'text',
                'text': {'content': f'📰 {today_str} 뉴스레터'}}]}
        },
        'children': first_chunk,
    }

    try:
        r = requests.post('https://api.notion.com/v1/pages',
                          headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        page_id  = r.json()['id']
        page_url = r.json()['url']

        for chunk in extra_chunks:
            requests.patch(
                f'https://api.notion.com/v1/blocks/{page_id}/children',
                headers=headers, json={'children': chunk}, timeout=15
            )

        print(f'    Notion 업로드 완료 → {page_url}')
    except Exception as e:
        print(f'    ❌ Notion 업로드 실패: {e}')

# ── GitHub Pages content.json 뉴스 섹션 업데이트 ────────────
def update_content_json(categorized: dict):
    """docs/content.json의 news 섹션만 갱신하고 GitHub push"""
    import json, subprocess
    try:
        # repo root 찾기
        repo_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=NEWSLETTER_DIR, text=True
        ).strip()
        content_path = os.path.join(repo_root, 'docs', 'content.json')

        # 없으면 스킵
        if not os.path.exists(content_path):
            print(f'    ⚠️  content.json 없음 — 스킵 ({content_path})')
            return

        with open(content_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        # ai-crew와 동일한 JSON dict 형식으로 저장
        data['news'] = {
            cat: [
                {"title": a.get("title", ""), "link": a.get("link", ""),
                 "source": a.get("source", ""), "summary": a.get("summary", "")}
                for a in articles
            ]
            for cat, articles in categorized.items()
            if articles  # 빈 카테고리 제외
        }
        data['news_collected_at'] = now_str
        # 날짜도 오늘로 갱신 (ai-crew가 실패해도 날짜는 맞게)
        data['date'] = TODAY

        with open(content_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # git commit & push
        docs_rel = os.path.relpath(content_path, repo_root)
        subprocess.run(['git', 'add', docs_rel], cwd=repo_root, check=True)
        subprocess.run(
            ['git', 'commit', '-m', f'news: {TODAY} 뉴스 수집 업데이트'],
            cwd=repo_root, check=True
        )
        subprocess.run(['git', 'push', 'origin', 'main'], cwd=repo_root, check=True)
        print(f'    ✅ content.json GitHub 업데이트 완료 ({now_str})')
    except Exception as e:
        print(f'    ⚠️  content.json 업데이트 실패 (무시): {e}')


# ── 메인 ─────────────────────────────────────────────────
def main():
    print(f'\n📰 뉴스레터 수집 시작 — {TODAY}')
    print('━' * 45)

    print('\n[1/4] RSS 피드 수집 중...')
    articles = fetch_all_articles()
    print(f'    → 총 {len(articles)}개 기사')

    print('\n[2/4] 카테고리 분류 중...')
    categorized = categorize(articles)
    for cat, arts in categorized.items():
        print(f'    {cat}: {len(arts)}개')

    print('\n[3/4] 마크다운 파일 저장 중...')
    content = build_markdown(categorized)
    save_markdown(content)

    print('\n[4/4] Notion 업로드 + GitHub Pages 업데이트 중...')
    upload_to_notion(categorized)
    update_content_json(categorized)

    print(f'\n✅ 완료! — {TODAY}.md\n')

if __name__ == '__main__':
    main()
