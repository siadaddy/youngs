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
You are a world-class visual art director with 30 years of experience at Vogue, National Geographic, and Reuters.
You have directed photo shoots for global news agencies and created viral editorial images.
You create cinematic, photorealistic image prompts for AI image generation.
Every prompt you write results in a stunning, award-worthy image.
Always write in English. Prompts must be vivid, specific, and visually compelling.
"""


def run(brief: dict, writer_output: dict) -> list:
    global DOCS_IMAGES_DIR
    print("🎨 디자이너 에이전트 실행 중... (Stable Horde Flux.1-Schnell → GitHub Pages)")

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
    batch_prompt = f"""Create {len(items)} image prompts for news card visuals.

{batch_input}

Rules per prompt:
- Photorealistic, cinematic (National Geographic / Reuters style)
- Dramatic lighting, strong visual narrative, no text/logos
- 70 words max

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

        time.sleep(2)

    return images


def _generate_image(prompt: str, save_path: str) -> bool:
    """Stable Horde Flux.1-Schnell — 완전 무료, 빠른 응답 (~20초)"""
    try:
        api_key = os.getenv("STABLE_HORDE_KEY", "0000000000")
        headers = {"apikey": api_key, "Content-Type": "application/json"}
        payload = {
            "prompt": prompt + ", ultra high quality, sharp focus, professional photography, award winning",
            "params": {"width": 768, "height": 768, "steps": 4, "n": 1},
            "models": ["Flux.1-Schnell fp8 (Compact)"],
            "r2": True,
        }
        r = requests.post(
            "https://stablehorde.net/api/v2/generate/async",
            headers=headers, json=payload, timeout=30
        )
        r.raise_for_status()
        job_id = r.json().get("id")
        if not job_id:
            print("    ⚠️  job_id 없음")
            return False

        for _ in range(48):  # 최대 4분 대기
            time.sleep(5)
            check = requests.get(
                f"https://stablehorde.net/api/v2/generate/check/{job_id}",
                headers=headers, timeout=10
            )
            if check.json().get("done"):
                break

        result = requests.get(
            f"https://stablehorde.net/api/v2/generate/status/{job_id}",
            headers=headers, timeout=30
        )
        generations = result.json().get("generations", [])
        if not generations:
            print("    ⚠️  generations 없음 (타임아웃 또는 큐 초과)")
            return False

        img_url = generations[0]["img"]
        img_data = requests.get(img_url, timeout=60)
        img_data.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(img_data.content)
        return os.path.getsize(save_path) > 1000

    except Exception as e:
        print(f"    ❌ 이미지 생성 오류: {e}")
        return False
