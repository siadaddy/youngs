import requests, os
from dotenv import load_dotenv
load_dotenv('.env')
T = os.getenv('NOTION_TOKEN')
H = {'Authorization': f'Bearer {T}', 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json'}
PARENT = os.getenv('NOTION_NEWSLETTER_PARENT_ID')

# 뉴스레터 페이지 parent 확인
r = requests.get('https://api.notion.com/v1/pages/32eb395f-9fc6-81f7-83ac-c157058150cb', headers=H, timeout=10)
print('newsletter parent:', r.json().get('parent'))

# 최상위 목록
r2 = requests.get(f'https://api.notion.com/v1/blocks/{PARENT}/children?page_size=30', headers=H, timeout=10)
print('\n=== 최상위 페이지 ===')
for b in r2.json().get('results', []):
    if b.get('type') == 'child_page':
        print(' ', b['child_page']['title'])

# 크리에이터 페이지 하위 확인
creator_id = '32fb395f-9fc6-8169-b8ca-f9644b0d34f4'
r3 = requests.get(f'https://api.notion.com/v1/blocks/{creator_id}/children?page_size=30', headers=H, timeout=10)
print('\n=== 크리에이터 페이지 하위 ===')
for b in r3.json().get('results', []):
    if b.get('type') == 'child_page':
        print(' ', b['child_page']['title'])
