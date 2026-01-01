from __future__ import annotations

import asyncio
import json
from pathlib import Path

import aiohttp

from ..config import get_settings
from ..data_models import SourceVideo
from ..utils.logging import setup_logger

logger = setup_logger("transcript")


class TranscriptGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate(self, video: SourceVideo, audio_path: Path) -> Path:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for transcription")
        transcript_dir = self.settings.data_root / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = transcript_dir / f"{video.id}.json"

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.settings.openai_api_key}",
            }
            data = aiohttp.FormData()
            data.add_field("file", open(audio_path, "rb"), filename=audio_path.name, content_type="audio/wav")
            data.add_field("model", "whisper-1")
            async with session.post(
                "https://api.openai.com/v1/audio/transcriptions", data=data, headers=headers, timeout=120
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Whisper API error: {response.status} {text}")
                payload = await response.json()

        transcript_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        video.transcript_path = transcript_path
        logger.info("Transcribed %s to %s", video.id, transcript_path)
        return transcript_path

    def load_transcript_text(self, transcript_path: Path) -> str:
        with open(transcript_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if "text" in data:
            return data["text"]
        segments = [segment["text"] for segment in data.get("segments", [])]
        return " ".join(segments)
