import os, json, re
from datetime import date
from utils.gemini_client import ask_gemini

SYSTEM = """음악 큐레이터. JSON만 출력합니다."""

DOCS_PATH = os.path.join(os.path.dirname(__file__), '../../../docs')


def run() -> list:
    print("🎵 음악 큐레이터 실행 중...")

    prompt = """아래 장르별 조건에 맞는 음악 정확히 100곡을 추천해줘.

장르별 곡수 (반드시 정확히 지킬 것):
- 【2000년대 힙합】 정확히 15곡: 2000~2009년 발매 한국·미국 힙합 명곡 (예: Eminem, Jay-Z, Kanye West, 에픽하이, MC몽, 리쌍 등)
- 【최신 힙합】 정확히 10곡: 2020년 이후 발매 한국·미국 힙합 (예: 기리보이, 염따, Drake, Kendrick Lamar 등)
- 【러닝·업템포】 정확히 25곡: BPM 150~170 내외의 에너지 넘치는 곡, 러닝·운동 시 듣기 좋은 곡 (K-pop·팝·EDM·힙합 장르 무관, 단 BPM 높고 신나야 함)
- 【K-pop】 정확히 25곡: 최근 3년 이내 인기 K-pop (아이돌·솔로 무관, 다양한 그룹)
- 【여성 보컬 발라드】 정확히 25곡: 애절하고 감성적인 여성 보컬 발라드 (한국·팝 무관, 이별·그리움·슬픔 감성, 예: 아이유, 백아연, 헤이즈, Adele, Billie Eilish 등)

공통 조건:
- 한 아티스트당 최대 3곡
- 아티스트명은 영문 또는 한글 원어 표기
- 트롯, 클래식, 동요 절대 제외
- 각 카테고리 곡수를 반드시 정확히 맞출 것 — 틀리면 실패

각 곡에 다음을 포함:
- g: 카테고리 그대로 표기 (2000s힙합 / 최신힙합 / 러닝업템포 / K-pop / 여성발라드)
- s: 인기도 점수 1~10
- d: 한 줄 분위기 설명 (15자 이내)

아래 JSON 형식으로만 출력 (다른 텍스트 없이):
{"songs": [{"t": "곡제목", "a": "아티스트명", "g": "장르", "s": 점수, "d": "분위기설명"}, ...]}
"""

    raw = ask_gemini(prompt, system=SYSTEM, temperature=0.85,
                     json_mode=True, max_tokens=5000)
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        data  = json.loads(raw)
        songs = data.get("songs", [])
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        songs = json.loads(m.group()).get("songs", []) if m else []

    # 중복 제거 (t+a 기준)
    seen, unique = set(), []
    for s in songs:
        key = (s.get("t","").strip(), s.get("a","").strip())
        if key not in seen and key[0]:
            seen.add(key)
            unique.append({
                "t": key[0],
                "a": key[1],
                "g": s.get("g", "기타"),
                "s": s.get("s", 7),
                "d": s.get("d", ""),
            })

    print(f"  ✅ {len(unique)}곡 큐레이션 완료")
    return unique


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
