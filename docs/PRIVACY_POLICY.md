# Privacy Policy

**TikTok Health Nepal**
Last updated: September 7, 2026

## 1. Overview

TikTok Health Nepal is an open source health education video generator. This privacy policy explains how the application handles data.

## 2. Data We Collect

This application collects and stores the following data **locally on your device only**:

- **TikTok API Tokens**: OAuth access and refresh tokens required to publish videos to your TikTok account. These are stored in a local `.env` file that is never committed to version control.
- **Generated Content**: Videos, audio clips, and images generated during the pipeline process are stored locally in the `output/` and `assets/` directories.

## 3. Data We Do Not Collect

- We do not collect personal information
- We do not track user activity or analytics
- We do not store data on external servers
- We do not share any data with third parties
- We do not access your TikTok followers, messages, or personal profile data

## 4. TikTok API Usage

This application uses the TikTok Content Posting API to:

- Upload videos you have explicitly reviewed and approved
- Check your account eligibility for posting

The application only requests the minimum required permissions: `video.upload`, `video.publish`, and `user.info.basic`.

## 5. Third Party Services

The application uses the following external services for content generation:

- **Google Gemini API**: For generating health scripts and cartoon images. Text prompts are sent to Google's API. No personal data is included in these requests.
- **Google Text to Speech (gTTS)**: For generating Nepali audio narration. Only health education text is sent to this service.

## 6. Data Security

- API keys and tokens are stored in a `.env` file excluded from version control via `.gitignore`
- No credentials are hardcoded in source code
- All TikTok API communication uses HTTPS

## 7. Your Rights

You can:

- Delete all locally stored data at any time
- Revoke TikTok access by removing the app from your TikTok account settings
- Delete generated content from the `output/` directory

## 8. Changes to This Policy

Updates to this privacy policy will be reflected in this document with an updated date.

## 9. Contact

For privacy related questions, please open an issue on the [GitHub repository](https://github.com/amritbh/tiktok-health-nepal).
