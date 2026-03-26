import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# 뉴스레터 .md 파일이 저장된 디렉토리
NEWSLETTER_DIR = os.getenv(
    "NEWSLETTER_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "뉴스레터"),
)


def get_today_newsletter() -> str:
    """오늘 날짜 뉴스레터 .md 파일에서 텍스트 읽기 (Notion API 호출 없음, 빠름)"""
    today = date.today().strftime("%Y-%m-%d")
    path = os.path.join(NEWSLETTER_DIR, f"{today}.md")

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"오늘({today}) 뉴스레터 파일을 찾을 수 없습니다: {path}\n"
            "뉴스 수집 스크립트(newsletter_naver.py)가 먼저 실행됐는지 확인하세요."
        )

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    return text
