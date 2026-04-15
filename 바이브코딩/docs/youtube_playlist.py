#!/usr/bin/env python3
"""
AI 추천곡 → 유튜브 뮤직 플레이리스트 자동 생성
사용법: python3 youtube_playlist.py
"""

import os, json, sys
from datetime import datetime
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
CRED_FILE       = BASE_DIR / "client_secret.json"
TOKEN_FILE      = BASE_DIR / "token.json"

# 오늘 날짜 music_YYYY-MM-DD.json → 없으면 music.json 폴백
today = datetime.now().strftime("%Y-%m-%d")
MUSIC_FILE = BASE_DIR / f"music_{today}.json"
if not MUSIC_FILE.exists():
    MUSIC_FILE = BASE_DIR / "music.json"

CACHE_FILE      = BASE_DIR / "video_cache.json"
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def load_cache() -> dict:
    """곡 → videoId 캐시 로드"""
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_credentials():
    """OAuth 인증 — 최초 1회 브라우저 인증, 이후 token.json 재사용"""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 토큰 갱신 중...")
            creds.refresh(Request())
        else:
            print("🌐 브라우저에서 Google 계정 인증이 필요합니다...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CRED_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("✅ 인증 완료 — token.json 저장됨")

    return creds


def search_video_id(youtube, title: str, artist: str) -> str | None:
    """YouTube에서 곡 검색 → 첫 번째 videoId 반환"""
    query = f"{artist} {title} official"
    try:
        res = youtube.search().list(
            part="id",
            q=query,
            type="video",
            videoCategoryId="10",  # Music 카테고리
            maxResults=1,
        ).execute()
        items = res.get("items", [])
        if items:
            return items[0]["id"]["videoId"]
    except Exception as e:
        print(f"  ⚠️  검색 실패 ({artist} - {title}): {e}")
    return None


def create_playlist(youtube, title: str, description: str) -> str:
    """플레이리스트 생성 → playlistId 반환"""
    res = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
            },
            "status": {"privacyStatus": "private"},  # 비공개로 생성
        },
    ).execute()
    return res["id"]


def add_to_playlist(youtube, playlist_id: str, video_id: str):
    """플레이리스트에 영상 추가 (3회 재시도)"""
    import time
    for attempt in range(3):
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()
            return
        except Exception as e:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                raise


def main():
    # ── 인증 ──────────────────────────────────────────────
    if not CRED_FILE.exists():
        print(f"❌ client_secret.json 없음: {CRED_FILE}")
        sys.exit(1)

    creds = get_credentials()

    from googleapiclient.discovery import build
    youtube = build("youtube", "v3", credentials=creds)

    # ── 음악 데이터 로드 ───────────────────────────────────
    if not MUSIC_FILE.exists():
        print(f"❌ 음악 파일 없음: {MUSIC_FILE}")
        sys.exit(1)

    with open(MUSIC_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    songs = data.get("songs", [])
    if not songs:
        print("❌ 추천곡 없음")
        sys.exit(1)

    print(f"🎵 {len(songs)}곡 로드 완료 ({MUSIC_FILE.name})")

    # ── 플레이리스트 생성 (또는 기존 ID 재사용) ────────────
    # 커맨드라인 인수로 기존 플레이리스트 ID 전달 가능
    # 예: python3 youtube_playlist.py PLxxxxxx
    if len(sys.argv) > 1 and sys.argv[1].startswith("PL"):
        playlist_id = sys.argv[1]
        print(f"♻️  기존 플레이리스트 이어서 추가: {playlist_id}")
    else:
        playlist_title = f"AI 추천 플레이리스트 {today}"
        playlist_desc  = f"AI가 {today}에 추천한 {len(songs)}곡\n자동 생성됨"
        playlist_id = create_playlist(youtube, playlist_title, playlist_desc)
        print(f"✅ 플레이리스트 생성: {playlist_title}")
    print(f"   https://music.youtube.com/playlist?list={playlist_id}")

    # ── 곡 검색 & 추가 ─────────────────────────────────────
    cache = load_cache()
    added = 0
    failed = []
    cache_hit = 0
    for i, song in enumerate(songs, 1):
        title  = song.get("t", "")
        artist = song.get("a", "")
        cache_key = f"{artist}|{title}"

        # 캐시 확인 — 있으면 검색 스킵 (API 할당량 절약)
        if cache_key in cache:
            video_id = cache[cache_key]
            print(f"  [{i:02d}/{len(songs)}] 캐시: {artist} - {title} ✅")
            cache_hit += 1
        else:
            print(f"  [{i:02d}/{len(songs)}] 검색 중: {artist} - {title}", end=" ")
            video_id = search_video_id(youtube, title, artist)
            if video_id:
                cache[cache_key] = video_id
                save_cache(cache)
                print("✅")
            else:
                print("❌ 검색 실패")
                failed.append(f"{artist} - {title}")
                continue

        add_to_playlist(youtube, playlist_id, video_id)
        added += 1

    # ── 결과 ───────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"🎉 완료! {added}/{len(songs)}곡 추가됨 (캐시 {cache_hit}곡 / 신규 검색 {added - cache_hit}곡)")
    print(f"🔗 유튜브 뮤직에서 열기:")
    print(f"   https://music.youtube.com/playlist?list={playlist_id}")
    if failed:
        print(f"\n⚠️  추가 실패 {len(failed)}곡:")
        for s in failed:
            print(f"   - {s}")


if __name__ == "__main__":
    main()
