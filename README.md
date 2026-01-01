# Viral Shorts Automation Platform

End-to-end automation for discovering trending long-form content, extracting viral hooks, editing Shorts with brand treatments, generating metadata, uploading to YouTube, and feeding analytics back into the loop.

## System Overview

- **Web Control Room** (`/webapp`) — Next.js dashboard for triggering runs, reviewing recent performance, and monitoring automation health. Designed for Vercel deployment.
- **Automation Engine** (`/automation`) — Python pipeline orchestrating discovery, AI analysis, editing, metadata generation, publishing, and analytics.
- **Data Lake** (`/data`) — Structured output for source manifests, rendered shorts, run logs, and analytics snapshots.

## Quickstart

```bash
# Install web dependencies
cd webapp
npm install

# Build and lint the dashboard
npm run lint
npm run build

# (Optional) create Python venv
cd ..
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Populate required environment variables (`OPENAI_API_KEY`, `YOUTUBE_API_KEY`, OAuth client secrets, etc.) before triggering the pipeline.

To execute a single automation run locally:

```bash
python -m automation.main
```

To keep the system running on a schedule:

```bash
python -m automation.scheduler
```

The Next.js dashboard interacts with the Python engine through `/api/pipeline`, spawning pipeline executions and surfacing the latest run statistics.

## Key Capabilities

- **Trending Discovery**: YouTube Data API plus TikTok/Instagram proxies evaluate velocity, engagement, and niche alignment.
- **Moment Selection**: Whisper transcription, transformer-based hook scoring, and audio energy analysis isolate 15–60s segments with strong openings.
- **Auto Editing**: FFmpeg + MoviePy convert to 9:16, add active reframes, captions, emojis, and brand CTA; background music layering supported.
- **Metadata Generation**: GPT-powered titles, descriptions, and hashtags tuned for Shorts.
- **Publishing**: YouTube API upload with scheduling, category assignment, and visibility control.
- **Analytics Feedback**: YouTube Analytics integration tracks retention, CTR, and surfacing signals to inform future cuts.

## Deployment

1. Deploy the dashboard: `cd webapp && npm run build`.
2. Verify `.vercel` configuration or run `vercel deploy --prod --yes --token $VERCEL_TOKEN --name agentic-9c3ecf5c`.
3. Confirm availability: `curl https://agentic-9c3ecf5c.vercel.app`.

## Extending the Pipeline

- Plug in additional discovery sources inside `automation/services/collectors.py`.
- Customize branding overlays in `automation/services/editor.py`.
- Experiment with hook scoring strategies in `automation/services/segmenter.py`.
- Integrate cloud storage or MLOps backends for scaling media processing.
