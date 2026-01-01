from __future__ import annotations

import json
import random

import openai

from ..config import get_settings
from ..data_models import SourceVideo, ViralSegment
from ..utils.logging import setup_logger

logger = setup_logger("metadata")


class MetadataGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        if self.settings.openai_api_key:
            openai.api_key = self.settings.openai_api_key

    def generate(self, segment: ViralSegment, video: SourceVideo) -> tuple[str, str, list[str]]:
        if not self.settings.openai_api_key:
            return self._fallback(segment, video)
        prompt = (
            "You are an expert YouTube Shorts growth strategist. "
            "Given the following context, craft a viral title, description, and hashtags.\n\n"
            f"Original video title: {video.title}\n"
            f"Segment transcript: {segment.transcript_snippet}\n"
            f"Keywords: {', '.join(segment.keywords)}\n"
            "Respond in JSON with fields: title, description, hashtags (list). "
            "Title 40-70 chars, include hook in first 2 seconds. "
            "Description should include CTA and summary."
        )
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You optimize YouTube Shorts metadata."}, {"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = response.choices[0].message["content"]
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse metadata response; falling back")
            return self._fallback(segment, video)
        title = payload.get("title", video.title[:70])
        description = payload.get("description", f"{segment.transcript_snippet[:140]}...")
        hashtags = payload.get("hashtags", ["#shorts", "#viral", "#trending"])
        return title, description, hashtags

    def _fallback(self, segment: ViralSegment, video: SourceVideo) -> tuple[str, str, list[str]]:
        keywords = segment.keywords or ["viral"]
        title = f"{keywords[0].capitalize()} secrets you must hear!"
        description = (
            f"🔥 Clip from {video.title}.\n"
            "Hit subscribe for more viral shorts and daily insights.\n"
            "#shorts #viral #trending"
        )
        hashtags = ["#shorts", "#viral", "#trending"] + [f"#{k}" for k in keywords[:2]]
        random.shuffle(hashtags)
        return title[:70], description, hashtags[:5]
