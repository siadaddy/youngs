#!/usr/bin/env python3
"""
🤖 시아아빠님의 AI 크리에이터
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
흐름:
  뉴스레터 읽기 (.md 파일)
    → 🎯 기획자 : 콘텐츠 브리프
    → ✍️  작가   : 카드뉴스 5개 + 블로그 아티클
    → 🎨 디자이너: 이미지 5장 → docs/images/ 저장
    → 🌐 GitHub Pages: content.json push → 사이트 자동 반영
    → 🔔 완료 알림 (ntfy.sh)

매일 07:00 KST 자동 실행 (launchd)
각 단계 실패 시 최대 3회 자동 재시도
"""

import sys, os, json, time, subprocess, requests
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from utils.notion_reader import get_today_newsletter, NEWSLETTER_DIR
from agents import planner, writer, designer, music_curator, weekly_trend
from dotenv import load_dotenv

load_dotenv()

NTFY_TOPIC  = os.getenv("NTFY_TOPIC", "siadad-aicrew")
MAX_RETRIES = 3          # 각 단계 최대 재시도 횟수
RETRY_DELAY = 10         # 재시도 대기 시간 (초)


def notify(title: str, message: str, priority: str = "default"):
    """ntfy.sh 푸시 알림 — JSON 방식 (한글 헤더 인코딩 오류 방지)"""
    priority_map = {"default": 3, "high": 4, "urgent": 5, "low": 2, "min": 1}
    try:
        requests.post(
            "https://ntfy.sh/",
            json={
                "topic":    NTFY_TOPIC,
                "title":    title,
                "message":  message,
                "priority": priority_map.get(priority, 3),
                "tags":     ["robot"],
            },
            timeout=5,
        )
    except Exception:
        pass


def retry(label: str, fn, *args, **kwargs):
    """fn(*args, **kwargs)을 최대 MAX_RETRIES번 재시도.
    성공하면 결과 반환, 모두 실패하면 마지막 예외를 다시 던진다.
    """
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                print(f"  ⚠️  [{label}] 실패 (시도 {attempt}/{MAX_RETRIES}): {e}")
                print(f"      {RETRY_DELAY}초 후 재시도...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"  ❌ [{label}] {MAX_RETRIES}회 모두 실패: {e}")
    raise last_err


GITHUB_PAGES_URL = "https://siadaddy.github.io/youngs/"


def main():
    today = date.today().strftime("%Y-%m-%d")

    print(f"\n🤖 시아아빠님의 AI 크리에이터 시작 — {today}")
    print("━" * 50)

    # ── Step 1: 뉴스레터 읽기 ────────────────────────────────
    print("\n[1/5] 오늘 뉴스레터 읽는 중...")
    try:
        newsletter = retry("뉴스레터 로드", get_today_newsletter)
        print(f"  ✅ 뉴스레터 로드 완료 ({len(newsletter)}자)")
    except Exception as e:
        notify("❌ AI 크리에이터 실패", f"뉴스레터 로드 실패: {e}", priority="high")
        sys.exit(1)

    newsletter_data = None
    data_path = os.path.join(NEWSLETTER_DIR, f"{today}_data.json")
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            newsletter_data = json.load(f)
        print(f"  ✅ 뉴스 데이터 로드 완료 ({len(newsletter_data.get('categorized', {}))}개 카테고리)")
    else:
        print(f"  ⚠️  뉴스 데이터 파일 없음: {data_path}")

    # ── Step 2: 기획자 ───────────────────────────────────────
    print("\n[2/5] 기획자 에이전트...")
    try:
        brief = retry("기획자", planner.run, newsletter, newsletter_data)
    except Exception as e:
        notify("❌ AI 크리에이터 실패", f"기획자 실패: {e}", priority="high")
        sys.exit(1)

    # ── Step 3: 작가 ─────────────────────────────────────────
    print("\n[3/5] 작가 에이전트...")
    try:
        written = retry("작가", writer.run, brief)
    except Exception as e:
        notify("❌ AI 크리에이터 실패", f"작가 실패: {e}", priority="high")
        sys.exit(1)

    # ── Step 4: 디자이너 ─────────────────────────────────────
    print("\n[4/5] 디자이너 에이전트...")
    try:
        images = retry("디자이너", designer.run, brief, written)
    except Exception as e:
        print(f"  ⚠️  이미지 생성 실패, 빈 이미지로 계속 진행: {e}")
        images = [{"headline": item["headline"], "prompt": "", "path": None,
                   "url": None, "success": False} for item in brief["instagram"]]

    # ── 결과 요약 ────────────────────────────────────────────
    img_ok = sum(1 for img in images if img["success"])

    summary = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 시아아빠님의 AI 크리에이터 완료!
   📰 카드뉴스    : {len(written['captions'])}개
   📝 블로그 아티클: 1개
   🖼  이미지       : {img_ok}/{len(images)}장
   🌐 GitHub Pages : {GITHUB_PAGES_URL}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(summary)

    notify(
        "✅ AI 크리에이터 완료",
        f"오늘 콘텐츠 준비됐어요!\n카드뉴스 {len(written['captions'])}개 · 이미지 {img_ok}장\n{GITHUB_PAGES_URL}",
    )

    # ── 음악 큐레이션 (주 1회) ──────────────────────────────
    print("\n[5/5] 음악 큐레이터 에이전트...")
    if _should_run_music():
        try:
            songs = retry("음악 큐레이터", music_curator.run)
            music_curator.save(songs)
            _create_youtube_playlist(songs, today)
        except Exception as e:
            print(f"  ⚠️  음악 큐레이션 실패: {e}")
            notify("⚠️ 음악 큐레이션 실패", f"music.json 미갱신\n오류: {e}", priority="high")
    else:
        print("  ⏭  음악 수집 스킵 (마지막 수집 7일 미경과)")

    # ── 주간 트렌드 브리핑 (월요일만) ───────────────────────
    if _should_run_weekly_trend():
        print("\n[6/6] 주간 트렌드 브리핑...")
        try:
            weekly_trend.run()
        except Exception as e:
            print(f"  ⚠️  주간 트렌드 실패 (무시): {e}")
            notify("⚠️ 주간 트렌드 생성 실패", f"오류: {e}", priority="low")
    else:
        print("\n[6/6] 주간 트렌드 스킵 (월요일 아님)")

    # ── GitHub Pages용 content.json 저장 & push ──────────────
    _publish_to_github(today, brief, written, images, newsletter_data)


def _should_run_weekly_trend() -> bool:
    """월요일(weekday=0)에만 실행"""
    return date.today().weekday() == 0


def _should_run_music() -> bool:
    """마지막 음악 수집이 7일 이상 지났으면 True"""
    import json
    from datetime import datetime, timedelta
    from pathlib import Path
    music_file = Path(__file__).parent.parent / "docs" / "music.json"
    if not music_file.exists():
        return True
    try:
        with open(music_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        updated = data.get("updated")
        if not updated:
            return True
        last = datetime.strptime(updated, "%Y-%m-%d")
        return (datetime.now() - last).days >= 7
    except Exception:
        return True


def _create_youtube_playlist(songs: list, today: str):
    """AI 추천곡을 유튜브 뮤직 플레이리스트로 자동 생성"""
    import sys
    from pathlib import Path

    script = Path(__file__).parent.parent / "docs" / "youtube_playlist.py"
    token  = Path(__file__).parent.parent / "docs" / "token.json"

    if not script.exists():
        print("  ⚠️  youtube_playlist.py 없음 — 스킵")
        return
    if not token.exists():
        print("  ⚠️  token.json 없음 — 첫 인증 필요, 유튜브 플레이리스트 스킵")
        notify("⚠️ 유튜브 뮤직 인증 필요",
               "token.json이 없습니다.\npython3 docs/youtube_playlist.py 를 한 번 수동 실행해 인증하세요.",
               priority="high")
        return

    print("  🎵 유튜브 뮤직 플레이리스트 생성 중...")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            # 플레이리스트 URL 추출
            for line in result.stdout.splitlines():
                if "music.youtube.com/playlist" in line:
                    url = line.strip()
                    print(f"  ✅ 유튜브 뮤직 플레이리스트 생성 완료")
                    print(f"     {url}")
                    notify("🎵 오늘의 플레이리스트 생성",
                           f"{len(songs)}곡 추가됨\n{url}", priority="default")
                    return
            print(f"  ✅ 유튜브 뮤직 플레이리스트 생성 완료")
        else:
            print(f"  ⚠️  유튜브 플레이리스트 생성 실패:\n{result.stderr[:300]}")
    except subprocess.TimeoutExpired:
        print("  ⚠️  유튜브 플레이리스트 생성 타임아웃 (5분 초과)")
    except Exception as e:
        print(f"  ⚠️  유튜브 플레이리스트 생성 오류: {e}")


def _publish_to_github(today, brief, written, images, newsletter_data):
    """결과물을 날짜별 JSON으로 저장하고 GitHub Pages에 push"""
    import html as html_lib
    repo_root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
    docs_dir     = os.path.join(repo_root, "docs")
    content_dir  = os.path.join(docs_dir, "content")
    os.makedirs(content_dir, exist_ok=True)

    payload = {
        "date": today,
        "blog_title": written.get("blog_title", ""),
        "captions": [
            {
                "headline":    c["headline"],
                "caption":     c["caption"],
                "image_url":   images[i]["url"] if i < len(images) else None,
                "source_url":  c.get("source_url", ""),
                "source_name": c.get("source_name", ""),
            }
            for i, c in enumerate(written["captions"])
        ],
        "article": written.get("article", ""),
        "news": {
            cat: [
                {
                    "title":   html_lib.unescape(a.get("title", "")),
                    "link":    a.get("link", ""),
                    "source":  a.get("source", ""),
                    "summary": html_lib.unescape(a.get("summary", "")),
                }
                for a in articles
            ]
            for cat, articles in (newsletter_data or {}).get("categorized", {}).items()
        } if newsletter_data else {},
        "news_collected_at": (newsletter_data or {}).get("collected_at", ""),
    }

    # 오늘 날짜 파일 저장 (아카이브용)
    daily_path = os.path.join(content_dir, f"{today}.json")
    with open(daily_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # 최신 콘텐츠 (오늘) — 사이트 기본 표시용
    latest_path = os.path.join(docs_dir, "content.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # archive.json — 날짜 목록 갱신
    archive_path = os.path.join(docs_dir, "archive.json")
    dates = []
    if os.path.exists(archive_path):
        with open(archive_path, "r", encoding="utf-8") as f:
            dates = json.load(f).get("dates", [])
    if today not in dates:
        dates.insert(0, today)          # 최신이 앞에
        dates = dates[:60]              # 최대 60일치 보관
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump({"dates": dates}, f, ensure_ascii=False, indent=2)

    try:
        subprocess.run(["git", "add", "docs/"], cwd=repo_root, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"content: {today} 카드뉴스 자동 업데이트"],
            cwd=repo_root, check=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True)
        print("  ✅ GitHub Pages 업데이트 완료")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  GitHub push 실패 (무시): {e}")


if __name__ == "__main__":
    main()
