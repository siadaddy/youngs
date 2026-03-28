import os, json, urllib.parse, subprocess, requests
from datetime import date
from utils.gemini_client import ask_gemini


def _get_images_dir():
    """docs/images/ 경로 (git repo 루트 기준). GitHub Actions에서 실제 저장에 사용."""
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
        d = os.path.join(repo_root, "docs", "images")
        os.makedirs(d, exist_ok=True)
        return d
    except Exception:
        return None

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

    images_dir = _get_images_dir()

    # ── 이미지 생성 ───────────────────────────────────────────
    images = []
    for i, item in enumerate(items):
        img_prompt = prompt_map.get(i + 1, item["headline"])
        print(f"  🖼  이미지 {i+1}/{len(items)}: {item['headline'][:30]}...")
        url = _generate_image(img_prompt, today, i + 1, images_dir)
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
        pollinations_url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=768&height=768&nologo=true&model=flux&seed={seed}"
        )

        # GitHub Actions에서 실행 시 이미지 다운로드 → GitHub Pages URL 사용
        # (Notion에서도 이미지 로드 가능)
        if images_dir:
            img_filename = f"{today}_{idx}.png"
            img_path = os.path.join(images_dir, img_filename)
            print(f"    ⬇️  이미지 다운로드 시도...")
            try:
                r = requests.get(
                    pollinations_url,
                    timeout=30,          # 30초 안에 응답 없으면 포기
                    allow_redirects=False,  # 401 리다이렉트 방지
                )
                ct = r.headers.get("content-type", "")
                if r.status_code == 200 and "image" in ct and len(r.content) > 5000:
                    with open(img_path, "wb") as f:
                        f.write(r.content)
                    gh_url = f"https://siadaddy.github.io/youngs/images/{img_filename}"
                    print(f"    💾 저장 완료 → {gh_url}")
                    return gh_url
                else:
                    print(f"    ⚠️  다운로드 불가 (status={r.status_code}) → URL 사용")
            except Exception as e:
                print(f"    ⚠️  다운로드 실패: {e} → URL 사용")

        return pollinations_url

    except Exception as e:
        print(f"    ❌ URL 생성 오류: {e}")
        return None
