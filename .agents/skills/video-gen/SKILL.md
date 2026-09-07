---
name: Video Generation
description: Generates TikTok health education videos for Nepal using Gemini AI, gTTS, and MoviePy. Covers the full pipeline from script generation to TikTok publishing with a gating workflow.
---

# Video Generation Skill

This skill automates the creation of short form public health education videos
targeting the general Nepali audience. Videos feature 2D cartoon style animations
with Nepali Devanagari captions and English subtitles.

## Pipeline Overview

### Step 1: Generate Video

```bash
python3 generator.py --topic "hand washing"
```

This runs three phases:
1. **Gemini Scripting**: Creates Do/Don't pairs in Nepali
2. **Asset Generation**: TTS audio (gTTS) + cartoon frames (Imagen 3)
3. **MoviePy Stitching**: Composites 9:16 vertical MP4

### Step 2: AI Review

```bash
python3 review.py
```

Uploads the video to Gemini multimodal for safety review.
Checks medical accuracy, subtitle clarity, and cultural fit.

### Step 3: Human Gate and Publish

```bash
python3 gate.py
```

Interactive three stage gate:
1. Displays AI review results
2. Opens video for local preview
3. Publish decision: Draft (inbox), Direct Post, or Skip

### TikTok OAuth Setup (One Time)

```bash
python3 tiktok_publisher.py auth
```

Opens browser for TikTok authorization. Tokens are saved to `.env`.

## Content Guidelines

1. All health advice must be medically accurate
2. Language should be simple, colloquial spoken Nepali
3. Visual style: bright, expressive 2D cartoons
4. Every scene must have a clear Do or Don't indicator
5. Videos target approximately 50 seconds runtime
6. Hashtags are always in English for discoverability
7. Captions are in Nepali with English subtitles

## File Structure

| File | Purpose |
|---|---|
| `generator.py` | Main video generation pipeline |
| `review.py` | AI safety and quality review |
| `gate.py` | Human approval gate before publishing |
| `tiktok_publisher.py` | TikTok OAuth and upload integration |
| `config.py` | Central configuration and path management |

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key |
| `TIKTOK_CLIENT_KEY` | TikTok developer app client key |
| `TIKTOK_CLIENT_SECRET` | TikTok developer app client secret |
| `TIKTOK_ACCESS_TOKEN` | Auto populated after OAuth flow |
| `TIKTOK_REFRESH_TOKEN` | Auto populated after OAuth flow |
