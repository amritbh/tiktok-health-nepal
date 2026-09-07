#!/usr/bin/env python3
"""
TikTok Health Nepal Video Generator

Three phase automated pipeline:
  Phase 1: Gemini generates a structured Do/Don't script in Nepali
  Phase 2: gTTS creates Nepali audio + Gemini Imagen 3 generates cartoon frames
  Phase 3: MoviePy stitches everything into a 9:16 vertical TikTok video

Usage:
  python3 generator.py --topic "hand washing"
  python3 generator.py --topic "dengue prevention" --dry-run
"""

import argparse
import json
import sys
import time
import textwrap
from pathlib import Path

from config import (
    GEMINI_API_KEY, GEMINI_TEXT_MODEL, GEMINI_IMAGE_MODEL,
    FONT_PATH, CHECK_IMAGE, CROSS_IMAGE,
    AUDIO_DIR, OUTPUT_DIR, IMAGES_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
    SCENE_COUNT, validate_gemini_key,
)


# ============================================================
# Phase 1: Gemini Script Generation
# ============================================================

def generate_script(topic: str) -> dict:
    """
    Use Gemini to generate a structured TikTok script
    with Do/Don't pairs in Nepali Devanagari.
    """
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)

    system_prompt = textwrap.dedent(f"""\
        You are an expert public health communicator in Nepal.
        Your audience is the general Nepali public including
        rural communities, young adults, and elderly people.

        Generate a TikTok video script about: "{topic}"

        Requirements:
        1. Create exactly {SCENE_COUNT} scenes as Do/Don't pairs
        2. Each scene has a "do" action and a "dont" action
        3. All text must be in simple, colloquial spoken Nepali (Devanagari script)
        4. Include an English translation for each caption
        5. Include a visual description for generating 2D cartoon illustrations
        6. The visual style should be: bright, expressive 2D cartoon animation
           featuring typical Nepali community members with clear visual cues

        Respond ONLY with valid JSON in this exact format:
        {{
          "title_nepali": "...",
          "title_english": "...",
          "hashtags": ["#PublicHealth", "#Nepal", "#HealthTips", ...],
          "scenes": [
            {{
              "pair_number": 1,
              "do": {{
                "nepali_text": "...",
                "english_text": "...",
                "visual_prompt": "Bright 2D cartoon: ..."
              }},
              "dont": {{
                "nepali_text": "...",
                "english_text": "...",
                "visual_prompt": "Bright 2D cartoon: ..."
              }}
            }}
          ]
        }}
    """)

    print("[Phase 1] Generating script with Gemini...")
    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=system_prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.8,
        },
    )

    raw_text = response.text.strip()
    script_data = json.loads(raw_text)

    scene_count = len(script_data.get("scenes", []))
    print(f"[Phase 1] Script generated: {script_data.get('title_nepali', '')}")
    print(f"[Phase 1] {scene_count} scene pairs created")

    # Save script to output for reference
    script_path = OUTPUT_DIR / "script.json"
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    print(f"[Phase 1] Script saved to {script_path}")

    return script_data


# ============================================================
# Phase 2: Asset Generation (TTS + Images)
# ============================================================

def generate_audio_clips(script_data: dict) -> list:
    """
    Generate Nepali text to speech audio for each scene
    using gTTS. Returns a list of audio file paths.
    """
    from gtts import gTTS

    print("[Phase 2] Generating Nepali audio clips...")
    audio_paths = []

    for scene in script_data["scenes"]:
        pair_num = scene["pair_number"]

        for scene_type in ["do", "dont"]:
            text = scene[scene_type]["nepali_text"]
            filename = f"scene_{pair_num}_{scene_type}.mp3"
            filepath = AUDIO_DIR / filename

            tts = gTTS(text=text, lang="ne", slow=False)
            tts.save(str(filepath))

            audio_paths.append({
                "path": filepath,
                "type": scene_type,
                "pair": pair_num,
                "nepali": text,
                "english": scene[scene_type]["english_text"],
            })
            print(f"  Audio: {filename}")

    print(f"[Phase 2] {len(audio_paths)} audio clips generated")
    return audio_paths


def generate_cartoon_frames(script_data: dict) -> list:
    """
    Generate 2D cartoon frames using Gemini Imagen 3.
    Falls back to colored placeholder frames if image generation fails.
    """
    from google import genai
    from PIL import Image, ImageDraw

    client = genai.Client(api_key=GEMINI_API_KEY)

    print("[Phase 2] Generating cartoon frames...")
    frame_paths = []

    for scene in script_data["scenes"]:
        pair_num = scene["pair_number"]

        for scene_type in ["do", "dont"]:
            prompt = scene[scene_type]["visual_prompt"]
            enhanced_prompt = (
                f"{prompt}. "
                "Style: bright colorful 2D cartoon illustration, "
                "clean lines, expressive characters, "
                "white background, suitable for health education, "
                "no text in image, 9:16 vertical aspect ratio."
            )

            filename = f"frame_{pair_num}_{scene_type}.png"
            filepath = IMAGES_DIR / filename

            try:
                response = client.models.generate_images(
                    model=GEMINI_IMAGE_MODEL,
                    prompt=enhanced_prompt,
                    config={
                        "number_of_images": 1,
                    },
                )

                if response.generated_images:
                    img_bytes = response.generated_images[0].image.image_bytes
                    with open(filepath, "wb") as f:
                        f.write(img_bytes)
                    print(f"  Frame: {filename} (Imagen 3)")
                else:
                    _create_placeholder_frame(filepath, scene_type, pair_num)
                    print(f"  Frame: {filename} (placeholder)")

            except Exception as e:
                print(f"  Frame: {filename} (placeholder, error: {e})")
                _create_placeholder_frame(filepath, scene_type, pair_num)

            frame_paths.append({
                "path": filepath,
                "type": scene_type,
                "pair": pair_num,
            })

    print(f"[Phase 2] {len(frame_paths)} frames generated")
    return frame_paths


def _create_placeholder_frame(filepath: Path, scene_type: str, pair_num: int):
    """Create a colored placeholder frame when image generation is unavailable."""
    from PIL import Image, ImageDraw, ImageFont

    bg_color = (232, 245, 233) if scene_type == "do" else (253, 232, 232)
    accent = (76, 175, 80) if scene_type == "do" else (244, 67, 54)

    img = Image.new("RGB", (1080, 1920), bg_color)
    draw = ImageDraw.Draw(img)

    # Draw a large circle with check or cross
    cx, cy, r = 540, 800, 200
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent)

    if scene_type == "do":
        # Checkmark
        draw.line([(cx - 80, cy), (cx - 20, cy + 60), (cx + 100, cy - 80)],
                  fill="white", width=20)
    else:
        # Cross
        draw.line([(cx - 70, cy - 70), (cx + 70, cy + 70)], fill="white", width=20)
        draw.line([(cx + 70, cy - 70), (cx - 70, cy + 70)], fill="white", width=20)

    # Label
    label = f"Scene {pair_num}: {'DO' if scene_type == 'do' else 'DO NOT'}"
    try:
        font = ImageFont.truetype(str(FONT_PATH), 48)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(((1080 - text_w) / 2, 1100), label, fill=accent, font=font)

    img.save(str(filepath))


# ============================================================
# Phase 3: MoviePy Video Stitching
# ============================================================

def render_text_overlay(text: str, font_size: int = 52, color: str = "white",
                        max_width: int = 960, bg_opacity: int = 180) -> Path:
    """
    Render Devanagari text to a PNG image using Pillow.
    This is more reliable than MoviePy TextClip for non Latin scripts.
    Returns the path to the rendered text image.
    """
    from PIL import Image, ImageDraw, ImageFont

    try:
        font = ImageFont.truetype(str(FONT_PATH), font_size)
    except Exception:
        font = ImageFont.load_default()

    # Wrap text to fit within max_width
    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)

    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = dummy_draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    if not lines:
        lines = [text]

    # Calculate dimensions
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = dummy_draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    line_spacing = 12
    total_h = sum(line_heights) + line_spacing * (len(lines) - 1)
    total_w = max(line_widths) if line_widths else max_width

    padding = 24
    img_w = total_w + padding * 2
    img_h = total_h + padding * 2

    # Create image with semi transparent dark background
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, bg_opacity))
    draw = ImageDraw.Draw(img)

    y_offset = padding
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (img_w - lw) / 2
        draw.text((x, y_offset), line, fill=color, font=font)
        y_offset += line_heights[i] + line_spacing

    # Save to a temp file
    text_hash = abs(hash(text)) % 100000
    text_img_path = AUDIO_DIR / f"_text_{text_hash}.png"
    img.save(str(text_img_path))
    return text_img_path


def stitch_video(script_data: dict, audio_clips: list, frame_paths: list) -> Path:
    """
    Compose all assets into a final 9:16 TikTok video using MoviePy 2.x.
    """
    from moviepy import (
        ImageClip, AudioFileClip, CompositeVideoClip,
        CompositeAudioClip, concatenate_videoclips,
    )

    print("[Phase 3] Stitching video...")
    scene_clips = []

    for i, audio_info in enumerate(audio_clips):
        frame_info = frame_paths[i]
        audio_path = str(audio_info["path"])
        frame_path = str(frame_info["path"])
        scene_type = audio_info["type"]

        # Load audio to get duration
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration + 0.5  # Add small padding

        # Background frame (resize to fill 1080x1920)
        bg_clip = (
            ImageClip(frame_path)
            .resized((VIDEO_WIDTH, VIDEO_HEIGHT))
            .with_duration(duration)
        )

        layers = [bg_clip]

        # Overlay check or cross icon
        icon_path = str(CHECK_IMAGE if scene_type == "do" else CROSS_IMAGE)
        if Path(icon_path).exists():
            icon_clip = (
                ImageClip(icon_path)
                .resized(height=120)
                .with_duration(duration)
                .with_position(("right", "top"))
                .with_effects([])
            )
            # Offset from edge
            icon_clip = icon_clip.with_position((VIDEO_WIDTH - 160, 40))
            layers.append(icon_clip)

        # Nepali caption (bottom area)
        nepali_text = audio_info["nepali"]
        nepali_img = render_text_overlay(nepali_text, font_size=56, color="white")
        nepali_overlay = (
            ImageClip(str(nepali_img))
            .with_duration(duration)
        )
        # Center horizontally, position near bottom
        nw = nepali_overlay.size[0]
        nx = (VIDEO_WIDTH - nw) / 2
        nepali_overlay = nepali_overlay.with_position((nx, VIDEO_HEIGHT - 400))
        layers.append(nepali_overlay)

        # English subtitle (smaller, below Nepali)
        english_text = audio_info["english"]
        eng_img = render_text_overlay(english_text, font_size=36, color="#E0E0E0",
                                      bg_opacity=140)
        eng_overlay = (
            ImageClip(str(eng_img))
            .with_duration(duration)
        )
        ew = eng_overlay.size[0]
        ex = (VIDEO_WIDTH - ew) / 2
        eng_overlay = eng_overlay.with_position((ex, VIDEO_HEIGHT - 300))
        layers.append(eng_overlay)

        # Composite scene
        scene = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
        scene = scene.with_duration(duration)
        scene = scene.with_audio(audio_clip)

        scene_clips.append(scene)
        label = "DO" if scene_type == "do" else "DO NOT"
        print(f"  Scene {audio_info['pair']}.{label}: {duration:.1f}s")

    # Title card
    title_nepali = script_data.get("title_nepali", "")
    title_english = script_data.get("title_english", "")
    title_text = f"{title_nepali}\n{title_english}"
    title_img = render_text_overlay(title_text, font_size=64, color="white",
                                    bg_opacity=200)

    title_card = (
        ImageClip(str(title_img))
        .with_duration(3)
        .with_position("center")
    )
    title_bg = (
        ImageClip(
            _create_gradient_background()
        )
        .with_duration(3)
    )
    title_scene = CompositeVideoClip(
        [title_bg, title_card],
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
    ).with_duration(3)
    scene_clips.insert(0, title_scene)

    # Concatenate all scenes
    final = concatenate_videoclips(scene_clips, method="compose")

    # Generate output filename
    topic_slug = script_data.get("title_english", "health_tip").lower()
    topic_slug = "".join(c if c.isalnum() else "_" for c in topic_slug)[:40]
    timestamp = int(time.time())
    output_path = OUTPUT_DIR / f"tiktok_{topic_slug}_{timestamp}.mp4"

    print(f"[Phase 3] Rendering to {output_path}...")
    final.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger="bar",
    )

    print(f"[Phase 3] Video saved: {output_path}")
    print(f"[Phase 3] Duration: {final.duration:.1f}s")

    # Save metadata alongside the video
    meta = {
        "title_nepali": script_data.get("title_nepali", ""),
        "title_english": script_data.get("title_english", ""),
        "hashtags": script_data.get("hashtags", []),
        "duration": final.duration,
        "output_file": str(output_path),
        "timestamp": timestamp,
    }
    meta_path = output_path.with_suffix(".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return output_path


def _create_gradient_background() -> str:
    """Create a gradient background image for the title card."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)

    # Deep blue to teal gradient
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        r = int(13 + ratio * 13)
        g = int(71 + ratio * 60)
        b = int(161 - ratio * 40)
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b))

    path = str(AUDIO_DIR / "_gradient_bg.png")
    img.save(path)
    return path


# ============================================================
# Main Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate a TikTok health education video for Nepal"
    )
    parser.add_argument(
        "--topic", type=str, default="hand washing",
        help="Health topic for the video (default: hand washing)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate setup without calling APIs"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  TikTok Health Nepal Video Generator")
    print(f"  Topic: {args.topic}")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] Validating setup...")
        print(f"  Font exists: {FONT_PATH.exists()}")
        print(f"  Check icon exists: {CHECK_IMAGE.exists()}")
        print(f"  Cross icon exists: {CROSS_IMAGE.exists()}")
        print(f"  Output dir exists: {OUTPUT_DIR.exists()}")
        print(f"  Audio dir exists: {AUDIO_DIR.exists()}")
        print(f"  Gemini key set: {'yes' if GEMINI_API_KEY else 'no'}")
        print(f"  Video dimensions: {VIDEO_WIDTH}x{VIDEO_HEIGHT}")
        print(f"  Target FPS: {VIDEO_FPS}")

        # Test imports
        try:
            from google import genai
            from moviepy import ImageClip
            from PIL import Image, ImageFont
            from gtts import gTTS
            print("  All imports: OK")
        except ImportError as e:
            print(f"  Import error: {e}")

        # Test font loading
        try:
            from PIL import ImageFont
            font = ImageFont.truetype(str(FONT_PATH), 48)
            print("  Font loading: OK")
        except Exception as e:
            print(f"  Font loading failed: {e}")

        print("\n[DRY RUN] Setup validation complete.")
        return

    # Full pipeline
    validate_gemini_key()

    # Phase 1: Generate script
    script_data = generate_script(args.topic)

    # Phase 2: Generate assets
    audio_clips = generate_audio_clips(script_data)
    frame_paths = generate_cartoon_frames(script_data)

    # Phase 3: Stitch video
    output_path = stitch_video(script_data, audio_clips, frame_paths)

    print("\n" + "=" * 60)
    print("  Pipeline complete!")
    print(f"  Video: {output_path}")
    print("  Next steps:")
    print("    python3 review.py    (AI safety review)")
    print("    python3 gate.py      (preview and publish)")
    print("=" * 60)


if __name__ == "__main__":
    main()
