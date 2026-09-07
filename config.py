"""
Central configuration for the TikTok Health Nepal pipeline.
Loads environment variables, defines paths, and sets video constants.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.resolve()
load_dotenv(PROJECT_ROOT / ".env")

# ============================================================
# API Keys
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "https://amritbh.github.io/tiktok-health-nepal/docs/")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN", "")

# ============================================================
# Directory Paths
# ============================================================
ASSETS_DIR = PROJECT_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
IMAGES_DIR = ASSETS_DIR / "images"
AUDIO_DIR = ASSETS_DIR / "audio"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Ensure output and audio directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Asset Paths
# ============================================================
FONT_PATH = FONTS_DIR / "NotoSansDevanagari-Variable.ttf"
CHECK_IMAGE = IMAGES_DIR / "check.png"
CROSS_IMAGE = IMAGES_DIR / "cross.png"

# ============================================================
# Video Constants (TikTok 9:16 vertical)
# ============================================================
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30
TARGET_DURATION_SECONDS = 50
SCENE_COUNT = 6  # Number of Do/Don't pairs

# ============================================================
# Gemini Model
# ============================================================
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "imagen-3.0-generate-002"

# ============================================================
# TikTok API Endpoints (v2)
# ============================================================
TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
TIKTOK_INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
TIKTOK_DIRECT_POST_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"


def validate_gemini_key():
    """Check that the Gemini API key is configured."""
    if not GEMINI_API_KEY:
        print("\n[ERROR] GEMINI_API_KEY is not set.")
        print("Add your key to the .env file:")
        print("  GEMINI_API_KEY=your_key_here\n")
        print("Get a free key at: https://aistudio.google.com/apikey")
        sys.exit(1)


def validate_tiktok_keys():
    """Check that TikTok API credentials are configured."""
    if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET:
        print("\n[ERROR] TikTok API credentials not set.")
        print("Add these to your .env file:")
        print("  TIKTOK_CLIENT_KEY=your_key")
        print("  TIKTOK_CLIENT_SECRET=your_secret\n")
        print("Register at: https://developers.tiktok.com/")
        sys.exit(1)


def validate_tiktok_tokens():
    """Check that TikTok access tokens exist (post OAuth flow)."""
    if not TIKTOK_ACCESS_TOKEN:
        print("\n[ERROR] TikTok access token not found.")
        print("Run the OAuth flow first:")
        print("  python3 tiktok_publisher.py auth\n")
        sys.exit(1)
