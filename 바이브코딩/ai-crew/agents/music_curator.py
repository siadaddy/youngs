import os, json, re
from datetime import date
from utils.gemini_client import ask_groq_first

SYSTEM = """음악 큐레이터. JSON만 출력합니다."""

DOCS_PATH = os.path.join(os.path.dirname(__file__), '../../docs')


def _extract_songs(raw: str) -> list:
    """손상된 JSON에서도 곡 목록을 최대한 추출하는 강건한 파서"""
    raw = raw.replace("```json", "").replace("```", "").strip()

    # 1단계: 그대로 파싱 시도
    try:
        data = json.loads(raw)
        return data.get("songs", [])
    except json.JSONDecodeError:
        pass

    # 2단계: songs 배열 시작점 찾아서 개별 객체 추출
    songs = []
    # songs 배열 시작 위치 탐색
    arr_start = raw.find('"songs"')
    if arr_start == -1:
        arr_start = 0
    bracket = raw.find('[', arr_start)
    if bracket == -1:
        bracket = raw.find('[')

    if bracket != -1:
        # 완전한 JSON 객체들만 추출 (불완전한 마지막 항목 제외)
        chunk = raw[bracket:]
        # 각 { ... } 블록을 개별 파싱
        depth = 0
        obj_start = None
        for i, ch in enumerate(chunk):
            if ch == '{':
                if depth == 0:
                    obj_start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and obj_start is not None:
                    obj_str = chunk[obj_start:i+1]
                    try:
                        obj = json.loads(obj_str)
                        if obj.get("t"):  # 제목 있는 항목만
                            songs.append(obj)
                    except json.JSONDecodeError:
                        pass
                    obj_start = None

    if songs:
        print(f"  ⚠️  JSON 복구: {len(songs)}곡 추출 성공")
    return songs


# 장르별 프롬프트 정의 (10곡씩 분리 호출 → JSON 잘림 방지)
GENRE_PROMPTS = [
    ("2000s힙합",  "2000~2009년 발매 해외(미국·영국) 힙합 명곡 10곡. Eminem·Jay-Z·Kanye West·50 Cent·Nelly·Ludacris·Lil Wayne 등. 한국 힙합 절대 제외."),
    ("최신힙합",   "2020년 이후 발매 해외(미국·영국) 힙합 10곡. Drake·Kendrick Lamar·Travis Scott·Post Malone·J. Cole·21 Savage 등. 한국 힙합 절대 제외."),
    ("러닝업템포", "BPM 140~180의 에너지 넘치는 러닝·운동용 곡 10곡. 장르 무관, 신나고 빠른 템포만."),
    ("K-pop",      "최근 3년 이내 인기 K-pop 남자 아이돌·솔로 10곡. 걸그룹 제외. BTS·EXO·Stray Kids·SEVENTEEN·NCT·ATEEZ 등."),
    ("여성발라드", "감성적인 여성 보컬 발라드 10곡. 한국·팝 무관. 이별·그리움 감성. 아이유·백아연·헤이즈·Adele·Billie Eilish·SZA 등."),
    ("걸그룹",     "최근 3년 이내 인기 K-pop 걸그룹 10곡. BLACKPINK·aespa·NewJeans·IVE·TWICE·LE SSERAFIM·ITZY·MAMAMOO 등."),
    ("최신곡",     "2024~2025년 발매 최신 해외 팝·R&B 10곡. 한국 곡 제외. Sabrina Carpenter·Charli XCX·Ariana Grande·Taylor Swift·The Weeknd·SZA 등."),
]


def _fetch_genre(genre_name: str, genre_desc: str) -> list:
    """장르 1개 10곡 수집 (실패 시 빈 리스트)"""
    prompt = f"""{genre_desc}

조건:
- 정확히 10곡, 한 아티스트당 최대 2곡
- 아티스트명은 영문 또는 한글 원어 표기
- 트롯·클래식·동요 절대 제외

JSON 형식으로만 출력 (설명 없이):
{{"songs":[{{"t":"곡제목","a":"아티스트명","g":"{genre_name}","s":인기도1~10,"d":"분위기15자이내"}},...]}}"""

    try:
        raw = ask_groq_first(prompt, system=SYSTEM, temperature=0.85,
                             json_mode=True, max_tokens=1500)
        songs = _extract_songs(raw)
        # g 값 강제 지정 (AI가 임의로 바꾸는 경우 대비)
        for s in songs:
            s["g"] = genre_name
        return songs
    except Exception as e:
        print(f"  ⚠️  [{genre_name}] 수집 실패: {e}")
        return []


def run() -> list:
    print("🎵 음악 큐레이터 실행 중... (장르별 분리 수집)")

    all_songs = []
    seen = set()

    for genre_name, genre_desc in GENRE_PROMPTS:
        print(f"  🎧 [{genre_name}] 수집 중...", end=" ", flush=True)
        songs = _fetch_genre(genre_name, genre_desc)

        # 중복 제거
        added = 0
        for s in songs:
            key = (s.get("t", "").strip(), s.get("a", "").strip())
            if key not in seen and key[0]:
                seen.add(key)
                all_songs.append({
                    "t": key[0],
                    "a": key[1],
                    "g": s.get("g", genre_name),
                    "s": s.get("s", 7),
                    "d": s.get("d", ""),
                })
                added += 1
        print(f"{added}곡 ✅" if added else "0곡 ⚠️")

    if not all_songs:
        raise ValueError("모든 장르 수집 실패")

    print(f"  ✅ 총 {len(all_songs)}곡 큐레이션 완료")
    return all_songs


def save(songs: list):
    import glob
    from datetime import datetime, timedelta
    today = date.today().isoformat()
    out = {"updated": today, "songs": songs}
    os.makedirs(DOCS_PATH, exist_ok=True)
    # music.json (현재)
    path = os.path.join(DOCS_PATH, "music.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    # music_YYYY-MM-DD.json (날짜별 히스토리)
    dated_path = os.path.join(DOCS_PATH, f"music_{today}.json")
    with open(dated_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"  💾 music.json + music_{today}.json 저장 완료 ({len(songs)}곡)")
    # 30일 초과 파일 자동 삭제
    cutoff = datetime.now() - timedelta(days=30)
    for f in glob.glob(os.path.join(DOCS_PATH, "music_????-??-??.json")):
        try:
            file_date = datetime.strptime(os.path.basename(f), "music_%Y-%m-%d.json")
            if file_date < cutoff:
                os.remove(f)
                print(f"  🗑  오래된 파일 삭제: {os.path.basename(f)}")
        except Exception:
            pass


if __name__ == "__main__":
    save(run())
