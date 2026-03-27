import os, requests, time, urllib.parse
# requests는 URL 구성에만 사용 (검증 요청 없음)
from datetime import date
from utils.gemini_client import ask_gemini

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

SYSTEM = """
You are a world-class visual art director with 30 years of experience at Vogue, National Geographic, and Reuters.
You have directed photo shoots for global news agencies and created viral editorial images.
You create cinematic, photorealistic image prompts for AI image generation.
Every prompt you write results in a stunning, award-worthy image.
Always write in English. Prompts must be vivid, specific, and visually compelling.
"""


def run(brief: dict, writer_output: dict) -> list:
    print("🎨 디자이너 에이전트 실행 중... (Pollinations.ai — 무료·즉시생성)")
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

        print(f"  🖼  이미지 {i+1}/5 생성 중: {item['headline'][:30]}...")

        url = _generate_image(image_prompt, today, i + 1)

        images.append({
            "headline": item["headline"],
            "prompt":   image_prompt,
            "path":     None,
            "url":      url,
            "success":  url is not None,
        })

        if url:
            print(f"  ✅ 이미지 {i+1} 생성 완료")
        else:
            print(f"  ⚠️  이미지 {i+1} 생성 실패")

        time.sleep(2)

    return images


def _generate_image(prompt: str, today: str, idx: int) -> str | None:
    """Pollinations.ai — URL을 구성해 반환.
    리다이렉트 추적 없이 원본 URL 그대로 반환 (Notion/사이트가 직접 로드).
    """
    try:
        seed = abs(hash(f"{today}-{idx}")) % 99999
        full_prompt = (
            prompt
            + ", ultra high quality, sharp focus, professional photography, award winning"
        )
        encoded = urllib.parse.quote(full_prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=768&height=768&nologo=true&model=flux&seed={seed}"
        )
        return url
    except Exception as e:
        print(f"    ❌ URL 생성 오류: {e}")
        return None
