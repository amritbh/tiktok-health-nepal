#!/usr/bin/env python3
"""
AI Safety Review for generated TikTok health videos.

Uploads the video to Gemini's multimodal endpoint and evaluates:
  1. Medical accuracy of health advice
  2. Subtitle readability and placement
  3. Cultural appropriateness for Nepali audience
  4. Visual clarity of Do/Don't indicators

Usage:
  python3 review.py
  python3 review.py --video output/tiktok_hand_washing_12345.mp4
"""

import argparse
import json
import sys
from pathlib import Path

from config import (
    GEMINI_API_KEY, GEMINI_TEXT_MODEL,
    OUTPUT_DIR, validate_gemini_key,
)


def find_latest_video() -> Path:
    """Find the most recently generated video in the output directory."""
    videos = sorted(OUTPUT_DIR.glob("tiktok_*.mp4"), key=lambda p: p.stat().st_mtime)
    if not videos:
        print("[ERROR] No videos found in output/ directory.")
        print("Run the generator first: python3 generator.py --topic 'your topic'")
        sys.exit(1)
    return videos[-1]


def review_video(video_path: Path) -> dict:
    """
    Upload video to Gemini multimodal endpoint
    and get a structured safety review.
    """
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)

    print(f"[Review] Uploading video: {video_path.name}")
    print("[Review] This may take a moment...")

    # Upload the video file
    video_file = client.files.upload(file=str(video_path))

    # Wait for processing
    import time
    while video_file.state.name == "PROCESSING":
        print("[Review] Processing video...")
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        print("[ERROR] Video processing failed.")
        sys.exit(1)

    review_prompt = """\
    You are a medical content reviewer and public health expert
    specializing in South Asian health communication.

    Review this TikTok health education video made for Nepal.
    Evaluate the following criteria and provide scores (0 to 100):

    1. MEDICAL_ACCURACY: Is the health advice scientifically correct?
       Are there any dangerous or misleading claims?
    2. SUBTITLE_CLARITY: Are the Nepali Devanagari subtitles readable?
       Is the font size adequate? Is placement good?
    3. CULTURAL_FIT: Is the content appropriate for the general
       Nepali public including rural communities?
    4. VISUAL_CLARITY: Are the Do/Don't indicators (green check, red cross)
       clearly visible and correctly placed?
    5. ENGAGEMENT: Would this video capture attention in a TikTok feed?

    Respond ONLY with valid JSON:
    {
      "overall_score": 85,
      "overall_verdict": "PASS",
      "categories": {
        "medical_accuracy": {"score": 90, "notes": "..."},
        "subtitle_clarity": {"score": 80, "notes": "..."},
        "cultural_fit": {"score": 85, "notes": "..."},
        "visual_clarity": {"score": 82, "notes": "..."},
        "engagement": {"score": 78, "notes": "..."}
      },
      "warnings": ["list any concerns here"],
      "suggestions": ["list improvement suggestions here"]
    }

    Verdicts: PASS (score >= 70), WARNING (50 to 69), FAIL (below 50)
    """

    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=[video_file, review_prompt],
        config={
            "response_mime_type": "application/json",
            "temperature": 0.3,
        },
    )

    review_data = json.loads(response.text.strip())

    # Clean up uploaded file
    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass

    return review_data


def display_review(review_data: dict):
    """Print a formatted review report to the terminal."""
    verdict = review_data.get("overall_verdict", "UNKNOWN")
    score = review_data.get("overall_score", 0)

    verdict_icon = {
        "PASS": "✅",
        "WARNING": "⚠️",
        "FAIL": "❌",
    }.get(verdict, "❓")

    print("\n" + "=" * 60)
    print(f"  {verdict_icon} AI REVIEW: {verdict} (Score: {score}/100)")
    print("=" * 60)

    categories = review_data.get("categories", {})
    for cat_name, cat_data in categories.items():
        cat_score = cat_data.get("score", 0)
        cat_notes = cat_data.get("notes", "")
        bar = "█" * (cat_score // 10) + "░" * (10 - cat_score // 10)
        label = cat_name.replace("_", " ").title()
        print(f"\n  {label}: [{bar}] {cat_score}/100")
        if cat_notes:
            print(f"    {cat_notes}")

    warnings = review_data.get("warnings", [])
    if warnings:
        print("\n  ⚠️  Warnings:")
        for w in warnings:
            print(f"    * {w}")

    suggestions = review_data.get("suggestions", [])
    if suggestions:
        print("\n  💡 Suggestions:")
        for s in suggestions:
            print(f"    * {s}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="AI safety review for TikTok health videos"
    )
    parser.add_argument(
        "--video", type=str, default=None,
        help="Path to the video file (default: latest in output/)"
    )

    args = parser.parse_args()
    validate_gemini_key()

    video_path = Path(args.video) if args.video else find_latest_video()

    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        sys.exit(1)

    print(f"[Review] Reviewing: {video_path.name}")

    review_data = review_video(video_path)
    display_review(review_data)

    # Save review report
    report_path = video_path.with_name(
        video_path.stem + "_review.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(review_data, f, ensure_ascii=False, indent=2)

    print(f"\n[Review] Full report saved: {report_path}")

    return review_data


if __name__ == "__main__":
    main()
