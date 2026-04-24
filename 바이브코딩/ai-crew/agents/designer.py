import os, json, re as _re, requests, time, subprocess
from datetime import date
from urllib.parse import quote
from dotenv import load_dotenv
from utils.gemini_client import ask_gemini
from utils.agent_memory import remember, get_hints

FALLBACK_FILENAME = "fallback.png"

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
    designer_hints = get_hints("최디자")
    batch_prompt = f"""Create {len(items)} image prompts for Korean SNS news card visuals.

{batch_input}

Style rules (MUST follow):
- Bright, vivid, optimistic colors — NO dark skies, NO explosions, NO suffering
- Clean modern aesthetic (Bloomberg / Wired magazine style)
- Use symbolic/conceptual visuals instead of literal war or disaster scenes
- Cars → sleek studio or open road in daylight. Economy → glowing charts or cityscapes. AI/Tech → clean futuristic interfaces
- No text, no logos, 70 words max per prompt{designer_hints}

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

        if not success:
            print(f"  ⚠️  이미지 {i+1} 생성 실패 → fallback 이미지 사용")
            fb_path = os.path.join(DOCS_IMAGES_DIR, FALLBACK_FILENAME)
            fb_url  = f"{GITHUB_PAGES_BASE}/{FALLBACK_FILENAME}"
            _ensure_fallback(fb_path)
            save_path = fb_path
            pages_url = fb_url
        else:
            print(f"  ✅ 이미지 {i+1} 저장 완료: docs/images/{filename}")

        images.append({
            "headline": item["headline"],
            "prompt":   img_prompt,
            "path":     save_path,
            "url":      pages_url,
            "success":  success,
        })
        keywords = [w for w in _re.sub(r'[^\w\s]', '', img_prompt).split() if len(w) > 3][:6]
        remember("최디자", "image_result", {
            "headline":        item["headline"],
            "prompt_keywords": keywords,
            "success":         success,
        })

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


def _ensure_fallback(path: str):
    """fallback.png 없으면 단색 그라디언트 이미지 자동 생성 (PIL)"""
    if os.path.exists(path):
        return
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (768, 768))
        draw = ImageDraw.Draw(img)
        # 위→아래 그라디언트: 진한 네이비 → 미드나잇 블루
        for y in range(768):
            t = y / 767
            r = int(10  + t * (28  - 10))
            g = int(15  + t * (45  - 15))
            b = int(40  + t * (100 - 40))
            draw.line([(0, y), (768, y)], fill=(r, g, b))
        img.save(path, "PNG")
        print(f"  🖼  fallback.png 자동 생성: {path}")
    except ImportError:
        # PIL 없으면 1x1 픽셀 최소 PNG 바이너리로 대체
        _write_minimal_png(path)
    except Exception as e:
        print(f"  ⚠️  fallback 생성 실패: {e}")
        _write_minimal_png(path)


def _write_minimal_png(path: str):
    """PIL 없을 때 최소 유효 PNG (1×1 네이비 픽셀) 저장"""
    import struct, zlib
    def chunk(name: bytes, data: bytes) -> bytes:
        c = name + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    header   = b'\x89PNG\r\n\x1a\n'
    ihdr     = chunk(b'IHDR', struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw_data = b'\x00\x0a\x0f\x28'       # filter byte + RGB (10,15,40)
    idat     = chunk(b'IDAT', zlib.compress(raw_data))
    iend     = chunk(b'IEND', b'')
    with open(path, "wb") as f:
        f.write(header + ihdr + idat + iend)
    print(f"  🖼  fallback.png (최소 PNG) 생성: {path}")
