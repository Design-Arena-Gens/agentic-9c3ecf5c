from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, HttpUrl, root_validator


class Platform(str, Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    PODCAST = "podcast"


class SourceVideo(BaseModel):
    id: str
    platform: Platform
    url: HttpUrl
    title: str
    channel_or_author: str
    language: str | None = None
    thumbnail_url: HttpUrl | None = None
    duration_seconds: int | None = None
    metrics: dict[str, Any] = {}
    downloaded_path: Path | None = None
    transcript_path: Path | None = None


class ViralSegment(BaseModel):
    source_video_id: str
    start_time: float
    end_time: float
    hook_score: float
    energy_score: float
    keywords: list[str]
    transcript_snippet: str

    @root_validator(pre=True)
    def ensure_order(cls, values: dict[str, Any]) -> dict[str, Any]:
        start = values.get("start_time", 0.0)
        end = values.get("end_time", 0.0)
        if end <= start:
            raise ValueError("Segment end_time must be greater than start_time")
        return values


class RenderedShort(BaseModel):
    segment: ViralSegment
    output_path: Path
    title: str
    description: str
    hashtags: list[str]
    scheduled_time: datetime | None = None
    upload_status: str = "pending"
    youtube_video_id: str | None = None


class PipelineResult(BaseModel):
    source: SourceVideo
    segments: list[ViralSegment]
    rendered_shorts: list[RenderedShort]
    analytics: dict[str, Any] = {}
    completed_at: datetime = datetime.utcnow()
