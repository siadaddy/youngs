import os, json, requests, time, subprocess
from datetime import date
from urllib.parse import quote
from dotenv import load_dotenv
from utils.gemini_client import ask_gemini

load_dotenv()

# 이미지를 docs/images/ 에 저장 → GitHub Pages로 서빙
def _repo_root():
    return subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()

DOCS_IMAGES_DIR  = None   # run() 첫 호출 시 초기화
GITHUB_PAGES_BASE = "https://siadaddy.github.io/youngs/images"

SYSTEM = """
You are a creative art director specializing in bright, modern news infographic visuals for Korean SNS and digital media.
Your style is clean, optimistic, and visually engaging — think Bloomberg, Wired, and The Economist cover art.
You create image prompts that feel fresh, energetic, and approachable — never dark, gloomy, or heavy.
Key rules:
- Always use bright, vivid colors (blues, greens, warm oranges, clean whites)
- Prefer symbolic or conceptual illustrations over realistic war/disaster imagery
- For economic news: upward graphs, glowing cityscapes, tech devices
- For car news: sleek studio shots, open roads, dynamic angles in daylight
- For AI/tech news: clean futuristic interfaces, glowing circuits, bright labs
- No dark skies, explosions, suffering, or dramatic shadows
- Always write in English. Keep prompts under 70 words.
"""


def run(brief: dict, writer_output: dict) -> list:
    global DOCS_IMAGES_DIR
    print("🎨 디자이너 에이전트 실행 중... (Pollinations.ai Flux → GitHub Pages)")

    # docs/images/ 폴더 초기화
    DOCS_IMAGES_DIR = os.path.join(_repo_root(), "docs", "images")
    os.makedirs(DOCS_IMAGES_DIR, exist_ok=True)

    today = date.today().strftime("%Y-%m-%d")

    # ── 3개 프롬프트를 API 1번 호출로 생성 ──────────────────────
    items = brief["instagram"]
    batch_input = "\n".join(
        f"{i+1}. headline: {it['headline']} | angle: {it['angle']} | tone: {it['tone']}"
        for i, it in enumerate(items)
    )
    batch_prompt = f"""Create {len(items)} image prompts for Korean SNS news card visuals.

{batch_input}

Style rules (MUST follow):
- Bright, vivid, optimistic colors — NO dark skies, NO explosions, NO suffering
- Clean modern aesthetic (Bloomberg / Wired magazine style)
- Use symbolic/conceptual visuals instead of literal war or disaster scenes
- Cars → sleek studio or open road in daylight. Economy → glowing charts or cityscapes. AI/Tech → clean futuristic interfaces
- No text, no logos, 70 words max per prompt

Return ONLY a JSON array, no markdown:
[{{"idx":1,"prompt":"..."}},{{"idx":2,"prompt":"..."}},...,{{"idx":{len(items)},"prompt":"..."}}]"""

    raw = ask_gemini(batch_prompt, system=SYSTEM, temperature=0.7, max_tokens=1500)
    raw = raw.strip().replace("```json", "").replace("```", "").strip()

    try:
        prompt_list = json.loads(raw)
        prompt_map = {p["idx"]: p["prompt"][:350] for p in prompt_list}
    except Exception as e:
        print(f"  ⚠️  프롬프트 JSON 파싱 실패: {e} — 기본값 사용")
        prompt_map = {i+1: items[i]["headline"] for i in range(len(items))}

    # ── 이미지 생성 & 저장 ────────────────────────────────────
    images = []
    for i, item in enumerate(items):
        img_prompt = prompt_map.get(i + 1, item["headline"])
        filename   = f"{today}_image_{i+1}.png"
        save_path  = os.path.join(DOCS_IMAGES_DIR, filename)
        pages_url  = f"{GITHUB_PAGES_BASE}/{filename}"

        print(f"  🖼  이미지 {i+1}/{len(items)} 생성 중: {item['headline'][:30]}...")
        success = _generate_image(img_prompt, save_path)

        images.append({
            "headline": item["headline"],
            "prompt":   img_prompt,
            "path":     save_path if success else None,
            "url":      pages_url if success else None,
            "success":  success,
        })

        if success:
            print(f"  ✅ 이미지 {i+1} 저장 완료: docs/images/{filename}")
        else:
            print(f"  ⚠️  이미지 {i+1} 생성 실패")

        # 이미지 사이 간격 — 첫 번째 실패 후엔 더 길게 대기
        time.sleep(15 if not success else 8)

    return images


def _generate_image(prompt: str, save_path: str) -> bool:
    """Pollinations.ai — 최대 3회 재시도, 429/5xx에 대기 후 재시도"""
    from urllib.parse import quote
    full_prompt = prompt + ", bright vivid colors, clean modern design, optimistic mood, high quality, sharp focus"
    encoded = quote(full_prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=768&height=768&model=flux&nologo=true&enhance=true"
    )

    wait_times = [0, 20, 40]   # 1차 즉시 / 2차 20초 후 / 3차 40초 후
    for attempt, wait in enumerate(wait_times, 1):
        if wait:
            print(f"    ⏳ {wait}초 후 재시도 ({attempt}/3)...")
            time.sleep(wait)
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 429:
                print(f"    ⚠️  429 Too Many Requests")
                continue
            if r.status_code >= 500:
                print(f"    ⚠️  {r.status_code} 서버 오류")
                continue
            r.raise_for_status()
            if len(r.content) < 1000:
                print("    ⚠️  응답 크기 너무 작음")
                continue
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
        except Exception as e:
            print(f"    ❌ 이미지 생성 오류: {e}")

    return False
