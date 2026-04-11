import os, json, re
from datetime import date
from utils.gemini_client import ask_gemini

SYSTEM = """음악 큐레이터. JSON만 출력합니다."""

DOCS_PATH = os.path.join(os.path.dirname(__file__), '../../../docs')


def run() -> list:
    print("🎵 음악 큐레이터 실행 중...")

    prompt = """지금 전 세계 및 한국에서 실제로 인기 있는 음악 70~80곡을 추천해줘.

장르 비율:
- K-pop (아이돌, 솔로): 약 30곡
- 한국 인디·팝·R&B·힙합: 약 15곡
- 팝 (미국·영국): 약 20곡
- R&B·힙합·일렉트로팝: 약 10곡

조건:
- 최근 2~3년 이내 발매 또는 여전히 차트에서 많이 듣는 곡 위주
- 트롯, 클래식, 동요, 어린이 음악 절대 제외
- 너무 오래된 올드팝도 최소화
- 다양한 아티스트 (한 아티스트당 최대 3곡)
- 아티스트명은 영문 또는 한글 원어 표기

각 곡에 다음을 포함:
- g: 아래 중 하나 (K-pop / 인디팝 / R&B / 힙합 / 팝 / 일렉트로팝 / 인디록 / 기타)
- s: 인기도 점수 1~10 (현재 차트 순위 기반)

아래 JSON 형식으로만 출력 (다른 텍스트 없이):
{"songs": [{"t": "곡제목", "a": "아티스트명", "g": "장르", "s": 점수}, ...]}
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
            })

    print(f"  ✅ {len(unique)}곡 큐레이션 완료")
    return unique


def save(songs: list):
    today = date.today().isoformat()
    out = {"updated": today, "songs": songs}
    os.makedirs(DOCS_PATH, exist_ok=True)
    # music.json (현재)
    path = os.path.join(DOCS_PATH, "music.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    # music_2026-04-11.json (날짜별 히스토리)
    dated_path = os.path.join(DOCS_PATH, f"music_{today}.json")
    with open(dated_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"  💾 music.json + music_{today}.json 저장 완료 ({len(songs)}곡)")


if __name__ == "__main__":
    save(run())
