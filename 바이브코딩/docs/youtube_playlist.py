#!/usr/bin/env python3
"""
AI 추천곡 → 유튜브 뮤직 고정 플레이리스트에 신곡만 추가
- 플레이리스트 이름 "AI 추천 플레이리스트"로 고정 (날짜 없음)
- 이미 추가된 곡은 건너뜀 → 날마다 새 곡만 누적
- playlist_state.json: 플레이리스트 ID + 추가된 곡 목록 보관
"""

import os, json, sys
from datetime import datetime
from pathlib import Path

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
CRED_FILE      = BASE_DIR / "client_secret.json"
TOKEN_FILE     = BASE_DIR / "token.json"
CACHE_FILE     = BASE_DIR / "video_cache.json"    # 곡명 → videoId 캐시
STATE_FILE     = BASE_DIR / "playlist_state.json" # 플레이리스트 ID + 추가된 곡 목록

PLAYLIST_TITLE = "AI 추천 플레이리스트"
SCOPES = ["https://www.googleapis.com/auth/youtube"]

today = datetime.now().strftime("%Y-%m-%d")

# 오늘 날짜 music_YYYY-MM-DD.json → 없으면 music.json 폴백
MUSIC_FILE = BASE_DIR / f"music_{today}.json"
if not MUSIC_FILE.exists():
    MUSIC_FILE = BASE_DIR / "music.json"


# ── 상태 파일 (플레이리스트 ID + 추가된 곡) ────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"playlist_id": None, "added": []}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ── videoId 캐시 ───────────────────────────────────────────
def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


# ── OAuth 인증 ─────────────────────────────────────────────
def get_credentials():
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


# ── YouTube API 헬퍼 ───────────────────────────────────────
def search_video_id(youtube, title: str, artist: str) -> str | None:
    query = f"{artist} {title} official"
    try:
        res = youtube.search().list(
            part="id",
            q=query,
            type="video",
            videoCategoryId="10",
            maxResults=1,
        ).execute()
        items = res.get("items", [])
        if items:
            return items[0]["id"]["videoId"]
    except Exception as e:
        print(f"  ⚠️  검색 실패 ({artist} - {title}): {e}")
    return None


def create_playlist(youtube) -> str:
    res = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": PLAYLIST_TITLE,
                "description": f"AI가 매일 추천하는 곡을 누적하는 플레이리스트\n마지막 업데이트: {today}",
            },
            "status": {"privacyStatus": "private"},
        },
    ).execute()
    return res["id"]


def add_to_playlist(youtube, playlist_id: str, video_id: str):
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


# ── 메인 ──────────────────────────────────────────────────
def main():
    if not CRED_FILE.exists():
        print(f"❌ client_secret.json 없음: {CRED_FILE}")
        sys.exit(1)

    creds = get_credentials()
    from googleapiclient.discovery import build
    youtube = build("youtube", "v3", credentials=creds)

    # 음악 파일 로드
    if not MUSIC_FILE.exists():
        print(f"❌ 음악 파일 없음: {MUSIC_FILE}")
        sys.exit(1)

    with open(MUSIC_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    songs = data.get("songs", [])
    if not songs:
        print("❌ 추천곡 없음")
        sys.exit(1)
    print(f"🎵 오늘의 추천곡 {len(songs)}곡 로드 ({MUSIC_FILE.name})")

    # 상태 로드 (플레이리스트 ID + 이미 추가된 곡 목록)
    state = load_state()
    playlist_id = state.get("playlist_id")
    added_set   = set(state.get("added", []))  # "아티스트|제목" 형태

    # 플레이리스트 없으면 신규 생성
    if not playlist_id:
        playlist_id = create_playlist(youtube)
        state["playlist_id"] = playlist_id
        save_state(state)
        print(f"✅ 플레이리스트 새로 생성: {PLAYLIST_TITLE}")
    else:
        print(f"♻️  기존 플레이리스트 재사용: {PLAYLIST_TITLE}")
    print(f"   https://music.youtube.com/playlist?list={playlist_id}")

    # 새 곡만 필터링
    new_songs = [s for s in songs if f"{s.get('a','')}|{s.get('t','')}" not in added_set]
    skip_count = len(songs) - len(new_songs)
    print(f"   → 이미 추가된 곡 {skip_count}곡 건너뜀 / 신규 {len(new_songs)}곡 추가 예정\n")

    if not new_songs:
        print("✅ 오늘 추천곡 모두 이미 플레이리스트에 있습니다.")
        return

    # 검색 & 추가
    cache    = load_cache()
    added    = 0
    failed   = []
    cache_hit = 0

    for i, song in enumerate(new_songs, 1):
        title     = song.get("t", "")
        artist    = song.get("a", "")
        cache_key = f"{artist}|{title}"

        if cache_key in cache:
            video_id = cache[cache_key]
            print(f"  [{i:02d}/{len(new_songs)}] 캐시: {artist} - {title} ✅")
            cache_hit += 1
        else:
            print(f"  [{i:02d}/{len(new_songs)}] 검색: {artist} - {title}", end=" ")
            video_id = search_video_id(youtube, title, artist)
            if video_id:
                cache[cache_key] = video_id
                save_cache(cache)
                print("✅")
            else:
                print("❌")
                failed.append(f"{artist} - {title}")
                continue

        try:
            add_to_playlist(youtube, playlist_id, video_id)
            added_set.add(cache_key)
            added += 1
            # 추가할 때마다 상태 저장 — 중간에 실패해도 진행분 보존
            state["added"] = list(added_set)
            state["last_updated"] = today
            save_state(state)
        except Exception as e:
            print(f"  ⚠️  플레이리스트 추가 실패: {e}")
            failed.append(f"{artist} - {title}")

    # 결과
    print(f"\n{'='*50}")
    print(f"🎉 완료! 신규 {added}/{len(new_songs)}곡 추가 (캐시 {cache_hit}곡 / 신규 검색 {added - cache_hit}곡)")
    print(f"   누적 총 {len(added_set)}곡")
    print(f"🔗 https://music.youtube.com/playlist?list={playlist_id}")
    if failed:
        print(f"\n⚠️  추가 실패 {len(failed)}곡:")
        for s in failed:
            print(f"   - {s}")


if __name__ == "__main__":
    main()
