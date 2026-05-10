#!/usr/bin/env python3
"""
📰 시아아빠님의 뉴스레터 자동 수집기
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
네이버 뉴스 API 수집 + Groq AI 요약 + TOP 3 선정 → 노션 업로드
매일 06:00 자동 실행 (crontab)
"""

import os, re, time, json, requests
from datetime import datetime, date
from dotenv import load_dotenv
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

def _sanitize(text: str) -> str:
    """한자·외계어 등 불필요한 문자 제거"""
    text = re.sub(r'[\u4e00-\u9fff]', '', text)   # CJK 통합 한자
    text = re.sub(r'[\u3400-\u4dbf]', '', text)   # CJK 확장 A
    text = re.sub(r'[\u3040-\u309f]', '', text)   # 히라가나
    text = re.sub(r'[\u30a0-\u30ff]', '', text)   # 가타카나
    text = re.sub(r'[\u0600-\u06ff]', '', text)   # 아랍어
    text = re.sub(r'[\u0e00-\u0e7f]', '', text)   # 태국어
    text = re.sub(r'[\u0400-\u04ff]', '', text)   # 키릴 (러시아어)
    text = re.sub(r'[\u0900-\u097f]', '', text)   # 데바나가리 (힌디어)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

load_dotenv()

NAVER_CLIENT_ID     = os.getenv('NAVER_CLIENT_ID', '')
NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET', '')
NOTION_TOKEN        = os.getenv('NOTION_TOKEN', '')
NOTION_PARENT_ID    = os.getenv('NOTION_PARENT_PAGE_ID', '329b395f9fc68169b2e8e7d06a621019')
NEWSLETTER_DIR      = os.getenv('NEWSLETTER_DIR', os.path.dirname(os.path.abspath(__file__)))
GROQ_KEYS           = [k for k in [os.getenv('GROQ_API_KEY'), os.getenv('GROQ_API_KEY_2')] if k]
TODAY               = date.today().strftime('%Y-%m-%d')
MAX_PER_CATEGORY    = 5

CATEGORIES = {
    '🔥 오늘의 하이라이트': ['속보', '단독', '오늘 주요뉴스'],
    '🤖 AI / 인공지능':    ['AI 인공지능', 'ChatGPT', '생성형 AI', 'LLM'],
    '💻 기술 / IT':       ['반도체 기술', '빅테크', 'IT 기업', '스타트업 기술'],
    '💰 경제 / 금융':      ['코스피 증시', '경제 금융', '부동산 시장', '환율 금리'],
    '🚨 사건 / 사고':      ['재난 안전', '자연재해', '소방 구조'],
    '🏙️ 사회':           ['사회 이슈', '정치 뉴스', '복지 정책'],
    '🚗 자동차':          ['전기차 자동차', '현대차 기아', '자율주행'],
    '🚘 BMW':            ['BMW 뉴스', 'BMW 신차'],
}

# ── AI 호출 ──────────────────────────────────────────────
def ask_ai(prompt: str, system: str = "") -> str:
    if not GROQ_KEYS:
        return ""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    for key_idx, api_key in enumerate(GROQ_KEYS):
        for attempt in range(1, 4):
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.4},
                    timeout=30,
                )
                if r.status_code == 429:
                    wait = min(int(r.headers.get("retry-after", 30)) + 5, 90)
                    print(f"    ⏳ Groq 키{key_idx+1} 속도 제한 — {wait}초 대기 ({attempt}/3)...")
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                return _sanitize(r.json()["choices"][0]["message"]["content"].strip())
            except Exception as e:
                if attempt == 3:
                    print(f"    ⚠️ Groq 키{key_idx+1} 실패: {e}")
        if key_idx < len(GROQ_KEYS) - 1:
            print(f"    ⚠️ Groq 키{key_idx+1} 소진 → 키{key_idx+2}로 전환...")
    return ""

def build_ai_summary(categorized: dict) -> dict:
    """카테고리 요약 + TOP 3 한 번에 생성"""
    print("  🤖 AI 요약 & TOP 3 생성 중...")
    all_articles = []
    for cat, arts in categorized.items():
        for a in arts:
            all_articles.append(f"[{cat}] [{a['source']}] {a['title']}: {a['summary']}")

    articles_text = "\n".join(all_articles)
    prompt = f"""오늘의 뉴스 기사들을 분석해주세요.

[오늘의 뉴스]
{articles_text}

아래 JSON 형식으로 정확히 응답하세요:
{{
  "top3": [
    {{"rank": 1, "title": "제목", "why": "중요한 이유 한 문장", "category": "카테고리명"}},
    {{"rank": 2, "title": "제목", "why": "중요한 이유 한 문장", "category": "카테고리명"}},
    {{"rank": 3, "title": "제목", "why": "중요한 이유 한 문장", "category": "카테고리명"}}
  ],
  "category_summaries": {{
    "카테고리명": "2~3문장 핵심 요약"
  }}
}}
JSON 외 다른 텍스트는 절대 포함하지 마세요."""

    raw = ask_ai(prompt, system="당신은 뉴스 분석 전문가입니다. 항상 JSON으로만 응답합니다.")
    if not raw:
        return {"top3": [], "category_summaries": {}}
    try:
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"    ⚠️ AI 요약 파싱 실패: {e}")
        return {"top3": [], "category_summaries": {}}

# ── 네이버 뉴스 검색 ─────────────────────────────────────
def search_naver_news(keyword, display=5):
    url = 'https://openapi.naver.com/v1/search/news.json'
    headers = {
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
    }
    params = {'query': keyword, 'display': display, 'sort': 'date'}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get('items', [])
    except Exception as e:
        print(f'    ⚠️  [{keyword}] 검색 실패: {e}')
        return []

def clean_html(text):
    return re.sub(r'<[^>]+>', '', text).strip()

def fetch_all():
    categorized = {}
    seen_links = set()
    for cat, keywords in CATEGORIES.items():
        articles = []
        for kw in keywords:
            if len(articles) >= MAX_PER_CATEGORY:
                break
            items = search_naver_news(kw, display=MAX_PER_CATEGORY)
            for item in items:
                link = item.get('originallink') or item.get('link', '')
                if link in seen_links:
                    continue
                seen_links.add(link)
                articles.append({
                    'title':   clean_html(item.get('title', '')),
                    'link':    link,
                    'summary': clean_html(item.get('description', ''))[:200],
                    'source':  extract_source(link),
                })
                if len(articles) >= MAX_PER_CATEGORY:
                    break
            time.sleep(0.2)
        categorized[cat] = articles
        print(f'    {cat}: {len(articles)}개')
    return categorized

def extract_source(url):
    mapping = {
        'yna.co.kr': '연합뉴스', 'ytn.co.kr': 'YTN',
        'mbc.co.kr': 'MBC', 'sbs.co.kr': 'SBS',
        'kbs.co.kr': 'KBS', 'hankyung.com': '한국경제',
        'etnews.com': '전자신문', 'heraldcorp.com': '헤럴드경제',
        'chosun.com': '조선일보', 'joongang.co.kr': '중앙일보',
        'donga.com': '동아일보', 'hani.co.kr': '한겨레',
        'khan.co.kr': '경향신문', 'ohmynews.com': '오마이뉴스',
    }
    for domain, name in mapping.items():
        if domain in url:
            return name
    return '뉴스'

# ── 마크다운 저장 ─────────────────────────────────────────
def save_markdown(categorized, ai_summary):
    today_str = date.today().strftime('%Y년 %m월 %d일')
    lines = [f'# 📰 뉴스레터 - {today_str}', '']

    top3 = ai_summary.get("top3", [])
    if top3:
        lines += ['## 📌 오늘의 TOP 3', '']
        for item in top3:
            lines.append(f'{item["rank"]}. **{item["title"]}** — {item["why"]}')
        lines += ['', '---', '']

    summaries = ai_summary.get("category_summaries", {})
    for cat, articles in categorized.items():
        lines.append(f'## {cat}')
        if summaries.get(cat):
            lines.append(f'> {summaries[cat]}')
            lines.append('')
        for a in articles:
            desc = f' — {a["summary"]}' if a['summary'] else ''
            lines.append(f'- **[{a["source"]}] [{a["title"]}]({a["link"]})**{desc}')
        lines.append('')

    lines += ['---', f'*수집 시각: {datetime.now().strftime("%Y-%m-%d %H:%M")}*']
    content = '\n'.join(lines)

    os.makedirs(NEWSLETTER_DIR, exist_ok=True)
    path = os.path.join(NEWSLETTER_DIR, f'{TODAY}.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'    저장 완료: {path}')

    # AI 크루가 읽을 수 있도록 JSON 데이터도 저장
    data_path = os.path.join(NEWSLETTER_DIR, f'{TODAY}_data.json')
    simplified = {cat: [{'title': a['title'], 'source': a['source'], 'link': a['link'], 'summary': a['summary']} for a in arts] for cat, arts in categorized.items()}
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump({'ai_summary': ai_summary, 'categorized': simplified, 'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M')}, f, ensure_ascii=False, indent=2)
    print(f'    데이터 저장 완료: {data_path}')

    insert_to_supabase(categorized, TODAY)


def insert_to_supabase(categorized, today):
    rows = []
    for cat, articles in categorized.items():
        for a in articles:
            rows.append({
                'date': today,
                'title': a['title'],
                'summary': a.get('summary', ''),
                'image_url': None,
                'category': cat
            })
    if rows:
        try:
            supabase_client.table('news_cards').insert(rows).execute()
            print(f'    [Supabase] {len(rows)}건 insert 완료')
        except Exception as e:
            print(f'    [Supabase] insert 실패: {e}')

# ── Notion 블록 헬퍼 ─────────────────────────────────────
def _t(text, bold=False, color="default"):
    ann = {}
    if bold:              ann["bold"] = True
    if color != "default": ann["color"] = color
    base = {"type": "text", "text": {"content": str(text)}}
    if ann: base["annotations"] = ann
    return base

# ── Notion 업로드 ─────────────────────────────────────────
def upload_to_notion(categorized, ai_summary):
    if not NOTION_TOKEN:
        print('    ⚠️  NOTION_TOKEN 없음')
        return

    today_str = date.today().strftime('%Y년 %m월 %d일')
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28',
    }

    blocks = []

    # 헤더 콜아웃
    blocks.append({
        'object': 'block', 'type': 'callout',
        'callout': {
            'rich_text': [_t(f'시아아빠님의 뉴스레터 · {today_str}  |  출처: 네이버 뉴스 API', bold=True)],
            'icon': {'emoji': '📰'},
        }
    })
    blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})

    # ── TOP 3 섹션 ──
    top3 = ai_summary.get("top3", [])
    if top3:
        blocks.append({
            'object': 'block', 'type': 'heading_2',
            'heading_2': {'rich_text': [_t('📌 오늘의 TOP 3')]}
        })
        rank_emojis = {1: '🥇', 2: '🥈', 3: '🥉'}
        for item in top3:
            emoji = rank_emojis.get(item['rank'], '•')
            blocks.append({
                'object': 'block', 'type': 'callout',
                'callout': {
                    'rich_text': [
                        _t(f'{item["title"]}', bold=True),
                        _t(f'\n{item["why"]}', color='gray'),
                    ],
                    'icon': {'emoji': emoji},
                    'color': 'yellow_background',
                }
            })
        blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})

    # ── 카테고리별 기사 ──
    summaries = ai_summary.get("category_summaries", {})
    for cat, articles in categorized.items():
        blocks.append({
            'object': 'block', 'type': 'heading_2',
            'heading_2': {'rich_text': [_t(cat)]}
        })

        # AI 요약 (있으면)
        if summaries.get(cat):
            blocks.append({
                'object': 'block', 'type': 'quote',
                'quote': {'rich_text': [_t(summaries[cat], color='gray')]}
            })

        if not articles:
            blocks.append({
                'object': 'block', 'type': 'paragraph',
                'paragraph': {'rich_text': [_t('수집된 기사 없음', color='gray')]}
            })
        else:
            for a in articles:
                desc = f'  {a["summary"][:100]}' if a['summary'] else ''
                blocks.append({
                    'object': 'block', 'type': 'bulleted_list_item',
                    'bulleted_list_item': {'rich_text': [
                        _t(f'[{a["source"]}] ', bold=True, color='blue'),
                        _t(a['title'], bold=True),
                        _t(desc, color='gray'),
                    ], 'color': 'default'}
                })
                # 링크를 별도 단락으로 추가
                if a['link']:
                    blocks.append({
                        'object': 'block', 'type': 'paragraph',
                        'paragraph': {'rich_text': [
                            {'type': 'text',
                             'text': {'content': '   🔗 기사 보기', 'link': {'url': a['link']}},
                             'annotations': {'color': 'blue', 'italic': True}}
                        ]}
                    })
        blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})

    # 푸터
    blocks.append({
        'object': 'block', 'type': 'paragraph',
        'paragraph': {'rich_text': [
            _t(f'수집 시각: {datetime.now().strftime("%Y-%m-%d %H:%M")}  ·  Powered by Naver API + Groq AI',
               color='gray')
        ]}
    })

    # AI 크루 구분선 — 뉴스레터 섹션 끝 표시 (AI 크루가 이어서 추가)
    blocks.append({'object': 'block', 'type': 'divider', 'divider': {}})
    blocks.append({
        'object': 'block', 'type': 'callout',
        'callout': {
            'rich_text': [_t('AI 크리에이터가 06:30 이후 이 페이지에 콘텐츠를 추가합니다...', color='gray')],
            'icon': {'emoji': '🤖'},
            'color': 'gray_background',
        }
    })

    # 청크 분할 업로드 (Notion API 한 번에 최대 100블록)
    chunks = [blocks[i:i+100] for i in range(0, len(blocks), 100)]
    payload = {
        'parent': {'page_id': NOTION_PARENT_ID},
        'icon': {'type': 'emoji', 'emoji': '🤖'},
        'properties': {'title': {'title': [{'type': 'text',
            'text': {'content': f'🤖 {today_str}'}}]}},
        'children': chunks[0],
    }
    try:
        r = requests.post('https://api.notion.com/v1/pages',
                          headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        page_id  = r.json()['id']
        page_url = r.json()['url']
        for chunk in chunks[1:]:
            requests.patch(f'https://api.notion.com/v1/blocks/{page_id}/children',
                           headers=headers, json={'children': chunk}, timeout=15)
        print(f'    Notion 업로드 완료 → {page_url}')
        return page_id  # page_id 반환 (AI 크루가 재사용)
    except Exception as e:
        print(f'    ❌ Notion 업로드 실패: {e}')
        return None

# ── 메인 ──────────────────────────────────────────────────
MAX_RETRIES  = 3
RETRY_DELAY  = 10  # 초


def _retry(label, fn, *args, **kwargs):
    """fn을 최대 MAX_RETRIES번 재시도. 모두 실패 시 마지막 예외를 던진다."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                print(f'  ⚠️  [{label}] 실패 (시도 {attempt}/{MAX_RETRIES}): {e}')
                print(f'      {RETRY_DELAY}초 후 재시도...')
                time.sleep(RETRY_DELAY)
            else:
                print(f'  ❌ [{label}] {MAX_RETRIES}회 모두 실패: {e}')
    raise last_err


def main():
    print(f'\n📰 시아아빠님의 뉴스레터 수집 시작 — {TODAY}')
    print('━' * 50)

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print('❌ NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 없음 → .env 확인')
        return

    print('\n[1/4] 뉴스 수집 중...')
    categorized = fetch_all()

    print('\n[2/4] AI 요약 & TOP 3 생성 중...')
    try:
        ai_summary = _retry('AI 요약', build_ai_summary, categorized)
        top3_count = len(ai_summary.get('top3', []))
        print(f'    TOP {top3_count}개 선정 완료')
    except Exception as e:
        print(f'  ⚠️  AI 요약 최종 실패, 빈 요약으로 계속 진행: {e}')
        ai_summary = {'top3': []}

    print('\n[3/4] 마크다운 저장 중...')
    _retry('마크다운 저장', save_markdown, categorized, ai_summary)

    # [4/4] Notion 업로드는 ai-crew/notion_publisher.py가 담당
    # → 06:30에 AI 크리에이터가 뉴스 원문 + AI 콘텐츠를 하나의 페이지로 통합 생성
    # → 여기서 별도로 업로드하면 같은 제목의 페이지가 2개 생성되므로 생략
    print('\n[4/4] Notion 업로드 — AI 크리에이터(06:30)가 통합 처리 예정, 스킵')

    print(f'\n✅ 뉴스레터 완료! — {TODAY}\n')

if __name__ == '__main__':
    main()
