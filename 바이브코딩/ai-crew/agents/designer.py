import os, requests, time, base64
from datetime import date
from utils.gemini_client import ask_gemini

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
HORDE_API_KEY = "0000000000"  # 익명 키 (무료)

SYSTEM = """
You are a world-class visual art director with 30 years of experience at Vogue, National Geographic, and Reuters.
You have directed photo shoots for global news agencies and created viral editorial images.
You create cinematic, photorealistic image prompts for AI image generation.
Every prompt you write results in a stunning, award-worthy image.
Always write in English. Prompts must be vivid, specific, and visually compelling.
"""

def run(brief: dict, writer_output: dict) -> list:
    print("🎨 디자이너 에이전트 실행 중... (Stable Horde — 무료)")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = date.today().strftime("%Y-%m-%d")
    images = []

    for i, item in enumerate(brief["instagram"]):
        prompt = f"""
Create a high-quality image prompt for a news card visual.

News headline: {item['headline']}
Angle: {item['angle']}
Tone: {item['tone']}

Requirements:
- Photorealistic, cinematic quality (like a National Geographic or Reuters editorial photo)
- Dramatic, purposeful lighting (golden hour, chiaroscuro, or moody atmospheric)
- Strong visual narrative — the image alone should tell the story
- Clear focal point, rule of thirds, professional composition
- Modern, sophisticated aesthetic — absolutely no text, no watermarks, no logos
- Evoke the emotion and gravity of the news story deeply
- Include: subject, setting, lighting style, color palette, mood, camera angle
- 70 words max, output the prompt text only

Example style: "A dramatic wide-angle shot of an empty trading floor at dawn, golden light streaming through floor-to-ceiling windows, casting long shadows across rows of dark monitors, lone security guard reflected in polished marble floor, cinematic color grading with deep teals and amber, photorealistic, 8k, Reuters editorial photography"
"""
        image_prompt = ask_gemini(prompt, system=SYSTEM, temperature=0.7)
        image_prompt = image_prompt.strip().replace('"', '')[:350]

        print(f"  🖼  이미지 {i+1}/5 생성 중: {item['headline'][:25]}...")

        save_path = os.path.join(OUTPUT_DIR, f"{today}_image_{i+1}.png")
        success = _generate_image(image_prompt, save_path)

        url = None
        if success:
            url = _upload_to_freeimage(save_path)

        images.append({
            "headline": item["headline"],
            "prompt": image_prompt,
            "path": save_path if success else None,
            "url": url,
            "success": success,
        })

        if success and url:
            print(f"  ✅ 이미지 {i+1} 저장 & 업로드: {url}")
        elif success:
            print(f"  ✅ 이미지 {i+1} 로컬 저장 (업로드 실패): {save_path}")
        else:
            print(f"  ⚠️  이미지 {i+1} 생성 실패")

        time.sleep(2)

    return images


def _generate_image(prompt: str, save_path: str) -> bool:
    """Stable Horde — 완전 무료, 커뮤니티 GPU 활용"""
    try:
        headers = {"apikey": HORDE_API_KEY, "Content-Type": "application/json"}
        payload = {
            "prompt": prompt + " | ultra high quality, sharp focus, professional photography, award winning",
            "params": {
                "width": 768, "height": 768,
                "steps": 35,
                "cfg_scale": 8.0,
                "sampler_name": "k_euler_a",
                "n": 1,
            },
            "models": ["ICBINP - I Can't Believe It's Not Photography"],
            "r2": True,
        }
        r = requests.post(
            "https://stablehorde.net/api/v2/generate/async",
            headers=headers, json=payload, timeout=30
        )
        r.raise_for_status()
        job_id = r.json()["id"]

        for _ in range(36):
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
        img_url = result.json()["generations"][0]["img"]

        img_data = requests.get(img_url, timeout=60)
        img_data.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(img_data.content)
        return os.path.getsize(save_path) > 1000
    except Exception as e:
        print(f"    ❌ 이미지 생성 오류: {e}")
        return False


def _upload_to_freeimage(path: str) -> str | None:
    """freeimage.host → 노션 임베드용 공개 URL 반환"""
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        r = requests.post(
            "https://freeimage.host/api/1/upload",
            data={
                "key": "6d207e02198a847aa98d0a2a901485a5",
                "action": "upload",
                "source": b64,
                "format": "json",
            },
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()["image"]["url"]
    except Exception as e:
        print(f"    ⚠️ 이미지 업로드 실패: {e}")
    return None
