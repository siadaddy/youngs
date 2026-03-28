import os, json, urllib.parse, subprocess
from datetime import date
from utils.gemini_client import ask_gemini

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

SYSTEM = """
You are a world-class visual art director. Create cinematic, photorealistic image prompts.
Always write in English. Output prompts only, no explanations.
"""


def run(brief: dict, writer_output: dict) -> list:
    print("🎨 디자이너 에이전트 실행 중... (Pollinations.ai)")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")

    # ── 5개 프롬프트를 API 1번 호출로 생성 ──────────────────────
    items = brief["instagram"]
    batch_input = "\n".join(
        f"{i+1}. headline: {it['headline']} | angle: {it['angle']} | tone: {it['tone']}"
        for i, it in enumerate(items)
    )
    batch_prompt = f"""Create 5 image prompts for news card visuals.

{batch_input}

Rules per prompt:
- Photorealistic, cinematic (National Geographic / Reuters style)
- Dramatic lighting, strong visual narrative, no text/logos
- 60 words max

Return ONLY a JSON array, no markdown:
[{{"idx":1,"prompt":"..."}},{{"idx":2,"prompt":"..."}},...,{{"idx":5,"prompt":"..."}}]"""

    raw = ask_gemini(batch_prompt, system=SYSTEM, temperature=0.7, max_tokens=1500)
    raw = raw.strip().replace("```json", "").replace("```", "").strip()

    try:
        prompt_list = json.loads(raw)
        prompt_map = {p["idx"]: p["prompt"][:350] for p in prompt_list}
    except Exception as e:
        print(f"  ⚠️  프롬프트 JSON 파싱 실패: {e} — 기본값 사용")
        prompt_map = {i+1: items[i]["headline"] for i in range(len(items))}

    # ── 이미지 생성 ───────────────────────────────────────────
    images = []
    for i, item in enumerate(items):
        img_prompt = prompt_map.get(i + 1, item["headline"])
        print(f"  🖼  이미지 {i+1}/{len(items)}: {item['headline'][:30]}...")
        url = _generate_image(img_prompt, today, i + 1)
        images.append({
            "headline": item["headline"],
            "prompt":   img_prompt,
            "path":     None,
            "url":      url,
            "success":  url is not None,
        })
        print(f"  {'✅' if url else '⚠️ '} 이미지 {i+1} {'완료' if url else '실패'}")

    return images


def _generate_image(prompt: str, today: str, idx: int, images_dir=None) -> str | None:
    try:
        seed = abs(hash(f"{today}-{idx}")) % 99999
        full_prompt = prompt + ", ultra high quality, sharp focus, professional photography"
        encoded = urllib.parse.quote(full_prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=768&height=768&nologo=true&model=flux&seed={seed}"
        )
        return url
    except Exception as e:
        print(f"    ❌ URL 생성 오류: {e}")
        return None
