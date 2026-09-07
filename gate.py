#!/usr/bin/env python3
"""
Human Approval Gate for the TikTok Health Nepal pipeline.

Three stage gating process:
  Stage 1: Displays AI review results
  Stage 2: Opens the video for local preview
  Stage 3: Prompts for publish decision (Draft / Direct / Skip)

Usage:
  python3 gate.py
  python3 gate.py --video output/tiktok_hand_washing_12345.mp4
"""

import argparse
import json
import subprocess
import sys
import platform
from pathlib import Path

from config import OUTPUT_DIR, validate_tiktok_tokens


def find_latest_video() -> Path:
    """Find the most recently generated video in the output directory."""
    videos = sorted(OUTPUT_DIR.glob("tiktok_*.mp4"), key=lambda p: p.stat().st_mtime)
    if not videos:
        print("[ERROR] No videos found in output/ directory.")
        print("Run the generator first: python3 generator.py --topic 'your topic'")
        sys.exit(1)
    return videos[-1]


def load_review(video_path: Path) -> dict:
    """Load the AI review report for a video if it exists."""
    review_path = video_path.with_name(video_path.stem + "_review.json")
    if review_path.exists():
        with open(review_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_metadata(video_path: Path) -> dict:
    """Load the video metadata (title, hashtags)."""
    meta_path = video_path.with_suffix(".json")
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def open_video_preview(video_path: Path):
    """Open the video in the system default media player."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", str(video_path)])
        elif system == "Linux":
            subprocess.Popen(["xdg-open", str(video_path)])
        elif system == "Windows":
            subprocess.Popen(["start", str(video_path)], shell=True)
        print(f"[Gate] Opened video preview: {video_path.name}")
    except Exception as e:
        print(f"[Gate] Could not open video automatically: {e}")
        print(f"[Gate] Please open manually: {video_path}")


def display_gate_prompt(video_path: Path, review_data: dict, metadata: dict):
    """Show the interactive approval gate in the terminal."""

    review_score = review_data.get("overall_score", "N/A") if review_data else "N/A"
    review_verdict = review_data.get("overall_verdict", "NOT REVIEWED") if review_data else "NOT REVIEWED"
    title = metadata.get("title_nepali", "")
    hashtags = " ".join(metadata.get("hashtags", []))

    verdict_icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌"}.get(review_verdict, "❓")

    print("\n")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║               TikTok Health Nepal Gate                  ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  📋 AI Review: {verdict_icon} {review_verdict} (Score: {review_score}/100)")
    print(f"║  🎬 Video: {video_path.name}")
    if title:
        print(f"║  📝 Title: {title}")
    if hashtags:
        print(f"║  # Tags: {hashtags}")
    print("║")
    print("║  What would you like to do?")
    print("║")
    print("║  [1] 📤 Upload as DRAFT to TikTok inbox")
    print("║      (Review in the TikTok app before posting)")
    print("║")
    print("║  [2] 🚀 Direct POST to TikTok")
    print("║      (Publishes immediately, requires app audit)")
    print("║")
    print("║  [3] ❌ Skip / Do not upload")
    print("║")
    print("╚══════════════════════════════════════════════════════════╝")

    if review_data and review_verdict == "FAIL":
        print("\n⚠️  WARNING: The AI review gave a FAIL verdict.")
        print("   It is recommended to regenerate the video before publishing.\n")


def build_caption(metadata: dict) -> str:
    """Build the TikTok post caption from metadata."""
    title_nepali = metadata.get("title_nepali", "")
    title_english = metadata.get("title_english", "")
    hashtags = metadata.get("hashtags", [])

    caption_parts = []
    if title_nepali:
        caption_parts.append(title_nepali)
    if title_english:
        caption_parts.append(title_english)
    if hashtags:
        caption_parts.append(" ".join(hashtags))

    return "\n".join(caption_parts)


def main():
    parser = argparse.ArgumentParser(
        description="Human approval gate for TikTok video publishing"
    )
    parser.add_argument(
        "--video", type=str, default=None,
        help="Path to the video file (default: latest in output/)"
    )
    parser.add_argument(
        "--skip-preview", action="store_true",
        help="Skip opening the video for local preview"
    )

    args = parser.parse_args()

    video_path = Path(args.video) if args.video else find_latest_video()
    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        sys.exit(1)

    # Load review and metadata
    review_data = load_review(video_path)
    metadata = load_metadata(video_path)

    if not review_data:
        print("[Gate] No AI review found for this video.")
        print("[Gate] Running review first is recommended: python3 review.py")
        run_review = input("[Gate] Run review now? (y/n): ").strip().lower()
        if run_review == "y":
            import review
            review_data = review.main()

    # Stage 2: Local preview
    if not args.skip_preview:
        open_video_preview(video_path)
        print("\n[Gate] Take a moment to watch the video...")
        input("[Gate] Press Enter when ready to continue...")

    # Stage 3: Publish decision
    display_gate_prompt(video_path, review_data, metadata)

    while True:
        choice = input("\nYour choice [1/2/3]: ").strip()

        if choice == "1":
            print("\n[Gate] Uploading as DRAFT to TikTok inbox...")
            validate_tiktok_tokens()
            from tiktok_publisher import upload_to_inbox
            caption = build_caption(metadata)
            success = upload_to_inbox(video_path, caption)
            if success:
                print("[Gate] ✅ Draft sent to your TikTok inbox!")
                print("[Gate] Open TikTok app to review and post.")
            else:
                print("[Gate] ❌ Upload failed. Check your TikTok credentials.")
            break

        elif choice == "2":
            print("\n[Gate] Publishing directly to TikTok...")
            validate_tiktok_tokens()
            from tiktok_publisher import direct_post
            caption = build_caption(metadata)
            success = direct_post(video_path, caption)
            if success:
                print("[Gate] ✅ Video published to TikTok!")
            else:
                print("[Gate] ❌ Direct post failed.")
                print("[Gate] This may require app audit approval from TikTok.")
            break

        elif choice == "3":
            print("\n[Gate] Skipped. Video saved locally at:")
            print(f"  {video_path}")
            break

        else:
            print("Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
