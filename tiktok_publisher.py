#!/usr/bin/env python3
"""
TikTok Content Posting API Integration (Sandbox Mode)

Handles:
  1. OAuth2 authorization flow with local callback server
  2. Token management (access + refresh)
  3. Video upload to TikTok inbox (draft)
  4. Direct post to TikTok
  5. Upload status polling

Usage:
  python3 tiktok_publisher.py auth       # Run OAuth flow
  python3 tiktok_publisher.py --check    # Verify credentials
"""

import argparse
import json
import os
import sys
import secrets
import hashlib
import base64
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

import requests

from config import (
    TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REDIRECT_URI,
    TIKTOK_ACCESS_TOKEN, TIKTOK_REFRESH_TOKEN,
    TIKTOK_AUTH_URL, TIKTOK_TOKEN_URL,
    TIKTOK_CREATOR_INFO_URL, TIKTOK_INBOX_INIT_URL,
    TIKTOK_DIRECT_POST_URL, TIKTOK_STATUS_URL,
    PROJECT_ROOT, validate_tiktok_keys, validate_tiktok_tokens,
)


# ============================================================
# OAuth2 Flow
# ============================================================

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth callback."""

    auth_code = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family:sans-serif;text-align:center;padding:60px;">
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                </body></html>
            """)
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"""
                <html><body style="font-family:sans-serif;text-align:center;padding:60px;">
                <h1>Authorization Failed</h1>
                <p>Error: {error}</p>
                </body></html>
            """.encode())

    def log_message(self, format, *args):
        """Suppress default HTTP log messages."""
        pass


def run_oauth_flow():
    """
    Launch the TikTok OAuth2 authorization flow.
    Opens browser, captures callback, exchanges for tokens.
    """
    validate_tiktok_keys()

    # Generate PKCE verifier and challenge
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('ascii')).digest()).decode('ascii').rstrip('=')

    # Build authorization URL
    csrf_state = f"tiktok_health_{int(time.time())}"
    auth_params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "response_type": "code",
        "scope": "user.info.basic,video.upload,video.publish",
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": csrf_state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{TIKTOK_AUTH_URL}?{urlencode(auth_params)}"

    # Parse callback port
    parsed_redirect = urlparse(TIKTOK_REDIRECT_URI)
    port = parsed_redirect.port or 8585

    print("\n[TikTok Auth] Starting OAuth2 flow...")
    print(f"[TikTok Auth] Callback server on port {port}")
    print(f"[TikTok Auth] Opening browser for authorization...\n")

    # Start local server
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    server.timeout = 120  # 2 minute timeout

    # Open browser
    webbrowser.open(auth_url)
    print("[TikTok Auth] Waiting for authorization (2 min timeout)...")

    # Wait for callback
    while OAuthCallbackHandler.auth_code is None:
        server.handle_request()

    auth_code = OAuthCallbackHandler.auth_code
    server.server_close()

    if not auth_code:
        print("[ERROR] Did not receive authorization code.")
        sys.exit(1)

    print("[TikTok Auth] Authorization code received!")
    print("[TikTok Auth] Exchanging for access token...")

    # Exchange code for tokens
    token_data = {
        "client_key": TIKTOK_CLIENT_KEY,
        "client_secret": TIKTOK_CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "code_verifier": code_verifier,
    }

    resp = requests.post(TIKTOK_TOKEN_URL, json=token_data)
    resp.raise_for_status()
    token_response = resp.json()

    access_token = token_response.get("access_token", "")
    refresh_token = token_response.get("refresh_token", "")
    expires_in = token_response.get("expires_in", 0)

    if not access_token:
        print(f"[ERROR] Token exchange failed: {token_response}")
        sys.exit(1)

    # Save tokens to .env
    _update_env_token("TIKTOK_ACCESS_TOKEN", access_token)
    _update_env_token("TIKTOK_REFRESH_TOKEN", refresh_token)

    print("\n[TikTok Auth] ✅ Tokens saved to .env!")
    print(f"[TikTok Auth] Access token expires in {expires_in} seconds")
    print("[TikTok Auth] You can now use gate.py to publish videos.\n")


def _update_env_token(key: str, value: str):
    """Update a specific key in the .env file."""
    env_path = PROJECT_ROOT / ".env"
    lines = []
    found = False

    if env_path.exists():
        with open(env_path, "r") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)


def refresh_access_token() -> str:
    """Refresh the TikTok access token using the refresh token."""
    if not TIKTOK_REFRESH_TOKEN:
        print("[ERROR] No refresh token available. Run: python3 tiktok_publisher.py auth")
        sys.exit(1)

    resp = requests.post(TIKTOK_TOKEN_URL, json={
        "client_key": TIKTOK_CLIENT_KEY,
        "client_secret": TIKTOK_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": TIKTOK_REFRESH_TOKEN,
    })
    resp.raise_for_status()
    data = resp.json()

    new_access = data.get("access_token", "")
    new_refresh = data.get("refresh_token", "")

    if new_access:
        _update_env_token("TIKTOK_ACCESS_TOKEN", new_access)
    if new_refresh:
        _update_env_token("TIKTOK_REFRESH_TOKEN", new_refresh)

    return new_access


# ============================================================
# Preflight Checks
# ============================================================

def preflight_check(video_path: Path) -> bool:
    """
    Validate the video file and TikTok account before upload.
    Checks format, size, and account eligibility.
    """
    print("[Preflight] Running pre upload checks...")

    # Check file exists and format
    if not video_path.exists():
        print(f"  [FAIL] Video file not found: {video_path}")
        return False

    if video_path.suffix.lower() != ".mp4":
        print(f"  [FAIL] Video must be MP4 format, got: {video_path.suffix}")
        return False

    # Check file size (TikTok limit: 4GB for direct, 128MB for inbox)
    size_mb = video_path.stat().st_size / (1024 * 1024)
    print(f"  [OK] File size: {size_mb:.1f} MB")
    if size_mb > 128:
        print("  [WARNING] File exceeds 128MB. Inbox upload may fail.")

    # Check creator info
    try:
        headers = {
            "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        resp = requests.post(TIKTOK_CREATOR_INFO_URL, headers=headers, json={})
        if resp.status_code == 200:
            info = resp.json()
            print(f"  [OK] TikTok account accessible")
        elif resp.status_code == 401:
            print("  [WARNING] Access token expired. Attempting refresh...")
            new_token = refresh_access_token()
            if new_token:
                print("  [OK] Token refreshed")
            else:
                print("  [FAIL] Could not refresh token. Run: python3 tiktok_publisher.py auth")
                return False
        else:
            print(f"  [WARNING] Creator info check returned: {resp.status_code}")
    except Exception as e:
        print(f"  [WARNING] Could not verify account: {e}")

    print("[Preflight] Checks passed.")
    return True


# ============================================================
# Upload Methods
# ============================================================

def upload_to_inbox(video_path: Path, caption: str) -> bool:
    """
    Upload video to the creator's TikTok inbox as a draft.
    They can review and post it from the TikTok app.
    """
    if not preflight_check(video_path):
        return False

    print("[Upload] Sending to TikTok inbox (draft)...")

    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    # Initialize inbox upload
    init_body = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_path.stat().st_size,
        },
    }

    try:
        resp = requests.post(TIKTOK_INBOX_INIT_URL, headers=headers, json=init_body)
        resp.raise_for_status()
        init_data = resp.json()

        publish_id = init_data.get("data", {}).get("publish_id", "")
        upload_url = init_data.get("data", {}).get("upload_url", "")

        if not upload_url:
            print(f"[Upload] Init failed: {init_data}")
            return False

        # Upload video file
        print("[Upload] Uploading video file...")
        with open(video_path, "rb") as f:
            video_data = f.read()

        upload_headers = {
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{len(video_data)-1}/{len(video_data)}",
        }

        upload_resp = requests.put(upload_url, headers=upload_headers, data=video_data)

        if upload_resp.status_code in (200, 201):
            print("[Upload] Video uploaded, waiting for processing...")
            return _poll_status(publish_id)
        else:
            print(f"[Upload] Upload failed: {upload_resp.status_code}")
            return False

    except Exception as e:
        print(f"[Upload] Error: {e}")
        return False


def direct_post(video_path: Path, caption: str) -> bool:
    """
    Publish video directly to TikTok (requires app audit approval).
    """
    if not preflight_check(video_path):
        return False

    print("[Upload] Publishing directly to TikTok...")

    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    init_body = {
        "post_info": {
            "title": caption[:150],  # TikTok title limit
            "privacy_level": "SELF_ONLY",  # Sandbox default: private
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_path.stat().st_size,
        },
    }

    try:
        resp = requests.post(TIKTOK_DIRECT_POST_URL, headers=headers, json=init_body)
        resp.raise_for_status()
        init_data = resp.json()

        publish_id = init_data.get("data", {}).get("publish_id", "")
        upload_url = init_data.get("data", {}).get("upload_url", "")

        if not upload_url:
            print(f"[Upload] Init failed: {init_data}")
            return False

        # Upload video file
        print("[Upload] Uploading video file...")
        with open(video_path, "rb") as f:
            video_data = f.read()

        upload_headers = {
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{len(video_data)-1}/{len(video_data)}",
        }

        upload_resp = requests.put(upload_url, headers=upload_headers, data=video_data)

        if upload_resp.status_code in (200, 201):
            print("[Upload] Video uploaded, waiting for processing...")
            return _poll_status(publish_id)
        else:
            print(f"[Upload] Upload failed: {upload_resp.status_code}")
            return False

    except Exception as e:
        print(f"[Upload] Error: {e}")
        return False


def _poll_status(publish_id: str, max_attempts: int = 12) -> bool:
    """
    Poll TikTok for the upload/publish status.
    Retries every 10 seconds up to max_attempts.
    """
    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    for attempt in range(max_attempts):
        time.sleep(10)
        try:
            resp = requests.post(
                TIKTOK_STATUS_URL,
                headers=headers,
                json={"publish_id": publish_id},
            )
            data = resp.json()
            status = data.get("data", {}).get("status", "PROCESSING")

            print(f"[Status] Attempt {attempt + 1}/{max_attempts}: {status}")

            if status == "PUBLISH_COMPLETE":
                return True
            elif status in ("FAILED", "PUBLISH_FAILED"):
                fail_reason = data.get("data", {}).get("fail_reason", "unknown")
                print(f"[Status] Publishing failed: {fail_reason}")
                return False

        except Exception as e:
            print(f"[Status] Polling error: {e}")

    print("[Status] Timed out waiting for publish confirmation")
    return False


# ============================================================
# Check Credentials
# ============================================================

def check_credentials():
    """Verify that all TikTok credentials are configured."""
    print("\n[Check] TikTok Credential Status")
    print("=" * 40)
    print(f"  Client Key:    {'✅ Set' if TIKTOK_CLIENT_KEY else '❌ Missing'}")
    print(f"  Client Secret: {'✅ Set' if TIKTOK_CLIENT_SECRET else '❌ Missing'}")
    print(f"  Redirect URI:  {TIKTOK_REDIRECT_URI}")
    print(f"  Access Token:  {'✅ Set' if TIKTOK_ACCESS_TOKEN else '❌ Missing (run auth)'}")
    print(f"  Refresh Token: {'✅ Set' if TIKTOK_REFRESH_TOKEN else '❌ Missing (run auth)'}")
    print("=" * 40)

    if TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET:
        if TIKTOK_ACCESS_TOKEN:
            print("\n✅ Ready to publish! Use: python3 gate.py")
        else:
            print("\n⚠️  Tokens missing. Run: python3 tiktok_publisher.py auth")
    else:
        print("\n❌ Register at https://developers.tiktok.com/")
        print("   Then add TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET to .env")


# ============================================================
# Main Entry Point
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="TikTok Content Posting API integration"
    )
    parser.add_argument(
        "action", nargs="?", default="check",
        choices=["auth", "check"],
        help="Action: 'auth' to run OAuth flow, 'check' to verify credentials"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Verify TikTok credentials"
    )

    args = parser.parse_args()

    if args.action == "auth":
        run_oauth_flow()
    else:
        check_credentials()


if __name__ == "__main__":
    main()
