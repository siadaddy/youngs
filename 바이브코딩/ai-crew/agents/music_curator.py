import os, json, re
from datetime import date
from utils.gemini_client import ask_gemini

SYSTEM = """음악 큐레이터. JSON만 출력합니다."""

DOCS_PATH = os.path.join(os.path.dirname(__file__), '../../../docs')


def run() -> list:
    print("🎵 음악 큐레이터 실행 중...")

    prompt = """지금 전 세계 및 한국에서 실제로 인기 있는 음악 75~80곡을 추천해줘.

장르 비율 (반드시 지킬 것):
- K-pop (아이돌, 솔로): 정확히 20곡
- 한국 인디·팝·R&B·힙합: 정확히 20곡
- 팝 (미국·영국): 정확히 20곡
- R&B·힙합·일렉트로팝: 정확히 15곡
- 기타 (재즈·보사노바·인디록): 5곡

조건:
- 최근 2~3년 이내 발매 또는 여전히 차트에서 많이 듣는 곡 위주
- 트롯, 클래식, 동요, 어린이 음악 절대 제외
- 너무 오래된 올드팝도 최소화
- 다양한 아티스트 (한 아티스트당 최대 3곡)
- 아티스트명은 영문 또는 한글 원어 표기
- 발라드는 전체의 20% 이하로 제한 — 업템포·중간 템포 곡 우선
- 슬로우 발라드만 나열하면 실패

인기도 점수 분포 (반드시 이 분포를 지킬 것):
- 9~10점: 10곡 (현재 1위권 차트 곡)
- 7~8점: 35곡 (상위권)
- 5~6점: 20곡 (중간)
- 1~4점: 10곡 (틈새/신예)
7~9점에 몰아주면 실패 — 분포를 고르게 배분할 것

각 곡에 다음을 포함:
- g: 아래 중 하나 (K-pop / 인디팝 / R&B / 힙합 / 팝 / 일렉트로팝 / 인디록 / 재즈 / 보사노바 / 기타)
- s: 인기도 점수 1~10 (위 분포 기준)
- d: 한 줄 분위기 설명 (15자 이내, 예: "몽환적인 밤의 감성", "에너지 넘치는 여름", "가슴 시린 이별")

아래 JSON 형식으로만 출력 (다른 텍스트 없이):
{"songs": [{"t": "곡제목", "a": "아티스트명", "g": "장르", "s": 점수, "d": "분위기설명"}, ...]}
"""

    raw = ask_gemini(prompt, system=SYSTEM, temperature=0.85,
                     json_mode=True, max_tokens=3000)
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
