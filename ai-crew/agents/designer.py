import os, json, re as _re, time, subprocess, textwrap
from datetime import date
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

        print(f"  🖼  이미지 {i+1}/{len(items)} PIL 카드 생성: {item['headline'][:30]}...")
        success = _generate_image_pil(item["headline"], i, save_path)

        if not success:
            print(f"  ⚠️  이미지 {i+1} PIL 생성 실패 → fallback 이미지 사용")
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
        remember("최디자", "image_result", {
            "headline": item["headline"],
            "success":  success,
        })

    # ── 자기 반성 & 성장 학습 ────────────────────────────────────
    try:
        from utils.agent_memory import (add_diary, get_persona, get_diary,
                                        should_update_persona, update_persona)
        success_cnt   = sum(1 for img in images if img["success"])
        failed_kws    = [img["prompt"].split()[:3] for img in images if not img["success"]]
        persona       = get_persona("최디자")
        recent        = " / ".join(e["lesson"][:25] for e in get_diary("최디자", 2)) or "첫 날"
        ctx = (f"이미지 {success_cnt}/{len(images)}장 성공. "
               + (f"실패 프롬프트 키워드: {failed_kws[:2]}" if failed_kws else "전체 성공!"))

        lesson_raw = ask_gemini(
            f"너는 AI 이미지 디자이너 '최디자'야.\n"
            f"지금까지 나: {persona[:60]}\n최근 메모: {recent}\n오늘 결과: {ctx}\n\n"
            "오늘 이미지 만들면서 느끼거나 배운 점 1문장. 1인칭 반말, 50자 이내.",
            temperature=0.85, max_tokens=80,
        )
        lesson = lesson_raw.strip().split("\n")[0][:150]
        if lesson:
            add_diary("최디자", lesson, trigger="daily_design")
            print(f"  📝 최디자 오늘의 학습: {lesson[:45]}")

        if should_update_persona("최디자"):
            diary_str = "\n".join(f"- {e['lesson']}" for e in get_diary("최디자", 7))
            new_p = ask_gemini(
                f"너는 AI 이미지 디자이너 '최디자'야.\n지금까지 나: {persona}\n"
                f"최근 학습 일기:\n{diary_str}\n\n"
                "이 경험을 바탕으로 지금의 나를 2문장으로. 1인칭 반말, 70자 이내.",
                temperature=0.8, max_tokens=120,
            ).strip().split("\n")[0][:300]
            if new_p:
                update_persona("최디자", new_p)
                print("  ✨ 최디자 페르소나 진화 완료")
    except Exception as e:
        print(f"  ⚠️  최디자 자기 반성 실패 (무시): {e}")

    return images


def _generate_image_pil(headline: str, card_index: int, save_path: str) -> bool:
    """PIL로 그라디언트+텍스트 카드 이미지 생성 (외부 API 없음)"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        W, H = 768, 768

        # 카드별 색상 테마: (배경_어두운, 배경_밝은, 액센트)
        themes = [
            ((8,  32,  88),  (30,  80, 180),  (100, 180, 255)),  # 블루
            ((80, 30,   8),  (200,  90,  30),  (255, 170,  90)),  # 오렌지
            ((8,  55,  28),  (28, 150,  80),  (100, 230, 150)),  # 그린
            ((45,  8,  75),  (130,  45, 195),  (210, 140, 255)),  # 퍼플
            ((8,  62,  75),  (28, 170, 195),  ( 90, 230, 245)),  # 틸
        ]
        dark, mid, accent = themes[card_index % len(themes)]

        # ── 배경 그라디언트 ──────────────────────────────────────
        bg = Image.new("RGB", (W, H))
        bg_draw = ImageDraw.Draw(bg)
        for y in range(H):
            t = y / H
            color = tuple(int(dark[i] + t * (mid[i] - dark[i])) for i in range(3))
            bg_draw.line([(0, y), (W, y)], fill=color)

        # ── RGBA 오버레이 (장식 원, 패널) ───────────────────────
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)

        # 우하단 큰 원
        for sz, alpha in [(300, 35), (210, 22), (130, 13)]:
            ov_draw.ellipse([W - sz, H - sz, W + sz // 2, H + sz // 2],
                            fill=accent + (alpha,))
        # 좌상단 작은 원
        for sz, alpha in [(160, 30), (100, 18)]:
            ov_draw.ellipse([-sz // 2, -sz // 2, sz, sz],
                            fill=accent + (alpha,))

        # 헤드라인 텍스트 패널 (반투명 어두운 박스)
        ov_draw.rectangle([55, H // 2 - 150, W - 55, H // 2 + 150],
                          fill=(0, 0, 0, 110))

        # 하단 accent bar
        ov_draw.rectangle([0, H - 10, W, H], fill=accent + (255,))

        # 카드 번호 뱃지
        bx, by, br = 58, 62, 28
        ov_draw.ellipse([bx - br, by - br, bx + br, by + br], fill=accent + (230,))

        # 합성
        result = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(result)

        # ── 폰트 로드 (한글 지원) ────────────────────────────────
        font_paths = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJKkr-Regular.otf",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        ]
        font_large = font_small = None
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font_large = ImageFont.truetype(fp, 50)
                    font_small = ImageFont.truetype(fp, 26)
                    break
                except Exception:
                    continue

        # ── 뱃지 숫자 ────────────────────────────────────────────
        badge_num = str(card_index + 1)
        if font_small:
            draw.text((bx, by), badge_num, fill=(10, 20, 50), font=font_small, anchor="mm")
        else:
            draw.text((bx - 6, by - 9), badge_num, fill=(10, 20, 50))

        # ── 헤드라인 텍스트 ──────────────────────────────────────
        lines = textwrap.wrap(headline, width=13)[:4]
        y_cursor = H // 2 - len(lines) * 33
        for line in lines:
            if font_large:
                bbox = draw.textbbox((0, 0), line, font=font_large)
                tw = bbox[2] - bbox[0]
                tx = (W - tw) // 2
                draw.text((tx + 2, y_cursor + 2), line, font=font_large, fill=(0, 0, 0))
                draw.text((tx, y_cursor), line, font=font_large, fill=(255, 255, 255))
            else:
                draw.text((W // 4, y_cursor), line[:20], fill=(255, 255, 255))
            y_cursor += 66

        # ── 사이트 푸터 ──────────────────────────────────────────
        footer = "siadaddy.github.io/youngs"
        if font_small:
            bbox = draw.textbbox((0, 0), footer, font=font_small)
            fw = bbox[2] - bbox[0]
            draw.text(((W - fw) // 2, H - 38), footer,
                      font=font_small, fill=(200, 220, 255))

        result.save(save_path, "PNG")
        return True

    except Exception as e:
        print(f"  ❌ PIL 카드 생성 실패: {e}")
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
