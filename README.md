# TikTok Health Nepal 🇳🇵

Automated pipeline that generates TikTok health education videos for the general public in Nepal. Each video features 2D cartoon style animations with clear "Do this / Don't do that" (गर्नुहोस् / नगर्नुहोस्) messaging in simple spoken Nepali.

## What It Does

This pipeline takes a health topic as input and produces a ready to publish TikTok video with:

- **Nepali Devanagari captions** for the primary audience
- **English subtitles** for accessibility
- **English hashtags** for global discoverability
- **Green checkmark / Red cross overlays** for instant visual clarity
- **AI powered safety review** before any video goes live
- **Three stage approval gate** so you always have final say before publishing

## Architecture

```
                    ┌─────────────────┐
                    │   Health Topic   │
                    │  "hand washing"  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   generator.py   │
                    │                  │
                    │  Phase 1: Gemini │
                    │  (Nepali script) │
                    │                  │
                    │  Phase 2: Assets │
                    │  (gTTS + Imagen) │
                    │                  │
                    │  Phase 3: Stitch │
                    │  (MoviePy 9:16)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    review.py     │
                    │  AI Safety Check │
                    │  Medical accuracy│
                    │  Cultural fit    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     gate.py      │
                    │  Local Preview   │
                    │  Human Approval  │
                    └────────┬────────┘
                             │
                  ┌──────────┼──────────┐
                  │          │          │
            ┌─────▼───┐ ┌───▼───┐ ┌───▼─────┐
            │  Draft   │ │Direct │ │  Skip   │
            │(Inbox)   │ │ Post  │ │         │
            └──────────┘ └───────┘ └─────────┘
```

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/YOUR_USERNAME/tiktok-health-nepal.git
cd tiktok-health-nepal
pip3 install -r requirements.txt
```

### 2. Add Your Gemini API Key

Get a free key from [Google AI Studio](https://aistudio.google.com/apikey) and add it to your `.env` file:

```bash
GEMINI_API_KEY=your_key_here
```

### 3. Generate a Video

```bash
python3 generator.py --topic "hand washing"
```

This will generate a 9:16 vertical MP4 in the `output/` folder.

### 4. Review and Publish

```bash
# AI safety review
python3 review.py

# Preview and publish gate
python3 gate.py
```

## TikTok Integration Setup

To publish videos to TikTok you need a developer account.

### 1. Register Your App

Go to [developers.tiktok.com](https://developers.tiktok.com/) and create an app. Enable the **Content Posting API** product and request `video.upload` and `video.publish` scopes.

### 2. Add Credentials

```bash
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_client_secret
```

### 3. Authorize Your Account

```bash
python3 tiktok_publisher.py auth
```

This opens your browser for TikTok authorization. After you approve, the access tokens are automatically saved to `.env`.

### 4. Verify Setup

```bash
python3 tiktok_publisher.py check
```

### Sandbox Mode

Until your TikTok app passes the audit review (usually 1 to 2 weeks), all uploads are restricted to **private/sandbox mode**. This is normal and expected. You can still:

- Upload videos as drafts to your TikTok inbox
- Preview them in the TikTok app
- Test the full pipeline end to end

Once approved, direct public posting becomes available.

## Three Stage Approval Gate

Nothing gets published without your explicit approval:

| Stage | What Happens | Who Decides |
|---|---|---|
| Stage 1 | AI reviews for medical accuracy, subtitle clarity, cultural fit | Automatic |
| Stage 2 | Video opens in your media player for local preview | You |
| Stage 3 | Choose: send to inbox as draft, post directly, or skip | You |

## Project Structure

```
tiktok-health-nepal/
├── .agents/skills/video-gen/
│   └── SKILL.md            # Agent skill documentation
├── .gitignore
├── .env                     # API keys (not committed)
├── README.md
├── requirements.txt
├── config.py                # Central configuration
├── generator.py             # Video generation pipeline
├── review.py                # AI safety review
├── gate.py                  # Human approval gate
├── tiktok_publisher.py      # TikTok OAuth and upload
├── assets/
│   ├── fonts/               # Noto Sans Devanagari font
│   ├── images/              # Check and cross icon overlays
│   └── audio/               # Generated TTS clips (working dir)
└── output/                  # Generated videos (gitignored)
```

## Tech Stack

| Component | Technology |
|---|---|
| Script Generation | Google Gemini (via google genai SDK) |
| Image Generation | Gemini Imagen 3 |
| Text to Speech | gTTS (Google Text to Speech, Nepali) |
| Video Compositing | MoviePy 2.x + FFmpeg |
| Text Rendering | Pillow with Noto Sans Devanagari font |
| TikTok Publishing | TikTok Content Posting API v2 |
| Secrets Management | python dotenv |

## Content Language

| Element | Language |
|---|---|
| Spoken narration (TTS) | Nepali |
| On screen captions | Nepali Devanagari |
| Subtitles | English |
| TikTok post caption | Nepali |
| Hashtags | English |

## Requirements

- Python 3.9+
- FFmpeg (for MoviePy video rendering)
- Gemini API key (free tier available)
- TikTok developer account (for publishing)

## Dry Run

To test the setup without using any API calls:

```bash
python3 generator.py --dry-run
```

## License

MIT
