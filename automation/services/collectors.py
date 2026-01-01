from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence

import aiohttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import get_settings
from ..data_models import Platform, SourceVideo
from ..utils.logging import setup_logger

logger = setup_logger("collectors")


class TrendingCollector:
    """Fetches trending videos across multiple platforms."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch_youtube_trending(self, niches: Sequence[str]) -> list[SourceVideo]:
        api_key = self.settings.youtube_api_key
        if not api_key:
            logger.warning("YOUTUBE_API_KEY missing; skipping YouTube trending scan")
            return []
        service = build("youtube", "v3", developerKey=api_key)
        results: list[SourceVideo] = []
        published_after = (datetime.utcnow() - timedelta(days=7)).isoformat("T") + "Z"

        for niche in niches:
            try:
                search_response = (
                    service.search()
                    .list(
                        q=niche,
                        part="id",
                        type="video",
                        maxResults=25,
                        publishedAfter=published_after,
                        order="viewCount",
                    )
                    .execute()
                )
            except HttpError as exc:
                logger.error("YouTube search error for niche %s: %s", niche, exc)
                continue

            video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
            if not video_ids:
                continue

            try:
                video_response = (
                    service.videos()
                    .list(
                        part="snippet,statistics,contentDetails",
                        id=",".join(video_ids),
                    )
                    .execute()
                )
            except HttpError as exc:
                logger.error("YouTube videos batch error: %s", exc)
                continue

            for item in video_response.get("items", []):
                snippet = item["snippet"]
                stats = item.get("statistics", {})
                duration = self._parse_iso_duration(item["contentDetails"]["duration"])
                results.append(
                    SourceVideo(
                        id=item["id"],
                        platform=Platform.YOUTUBE,
                        url=f"https://www.youtube.com/watch?v={item['id']}",
                        title=snippet["title"],
                        channel_or_author=snippet["channelTitle"],
                        language=snippet.get("defaultAudioLanguage"),
                        thumbnail_url=snippet["thumbnails"]["high"]["url"],
                        duration_seconds=duration,
                        metrics=self._build_metrics(stats),
                    )
                )
        return results

    async def fetch_tiktok_trending(self, niches: Sequence[str]) -> list[SourceVideo]:
        # TikTok does not expose an official public API; we proxy via a popular-trends endpoint.
        # For production use, integrate a third-party provider or official Marketing API.
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_tiktok_niche(session, niche) for niche in niches]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        videos: list[SourceVideo] = []
        for result in results:
            if isinstance(result, Exception):
                logger.debug("TikTok niche fetch error: %s", result)
                continue
            videos.extend(result)
        return videos

    async def _fetch_tiktok_niche(
        self, session: aiohttp.ClientSession, niche: str
    ) -> list[SourceVideo]:
        url = "https://www.tikwm.com/api/feed/search"
        payload = {"keywords": niche, "count": 10}
        async with session.post(url, data=payload, timeout=15) as response:
            if response.status != 200:
                logger.debug("TikTok API returned %s", response.status)
                return []
            data = await response.json()
        videos: list[SourceVideo] = []
        for item in data.get("data", {}).get("videos", []):
            metrics = {
                "digg_count": item.get("digg_count"),
                "share_count": item.get("share_count"),
                "comment_count": item.get("comment_count"),
                "play_count": item.get("play_count"),
            }
            videos.append(
                SourceVideo(
                    id=item["video_id"],
                    platform=Platform.TIKTOK,
                    url=item["play"],
                    title=item["title"] or niche,
                    channel_or_author=item["author"]["unique_id"],
                    language=item.get("language", "unknown"),
                    thumbnail_url=item.get("cover"),
                    duration_seconds=item.get("duration"),
                    metrics=metrics,
                )
            )
        return videos

    async def fetch_instagram_trending(self, niches: Sequence[str]) -> list[SourceVideo]:
        # Instagram does not provide an open API for reels; we rely on a third-party endpoint.
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_instagram_niche(session, niche) for niche in niches]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        videos: list[SourceVideo] = []
        for result in results:
            if isinstance(result, Exception):
                logger.debug("Instagram niche fetch error: %s", result)
                continue
            videos.extend(result)
        return videos

    async def _fetch_instagram_niche(
        self, session: aiohttp.ClientSession, niche: str
    ) -> list[SourceVideo]:
        url = "https://www.instaviews.io/api/trending"
        payload = {"tag": niche, "limit": 10}
        async with session.get(url, params=payload, timeout=15) as response:
            if response.status != 200:
                return []
            data = await response.json()
        videos: list[SourceVideo] = []
        for item in data.get("videos", []):
            metrics = {
                "likes": item.get("likes"),
                "plays": item.get("plays"),
                "comments": item.get("comments"),
            }
            videos.append(
                SourceVideo(
                    id=item["id"],
                    platform=Platform.INSTAGRAM,
                    url=item["permalink"],
                    title=item["title"] or niche,
                    channel_or_author=item["username"],
                    language=item.get("language", "unknown"),
                    thumbnail_url=item.get("thumbnail"),
                    duration_seconds=item.get("duration"),
                    metrics=metrics,
                )
            )
        return videos

    def persist_sources(self, sources: Iterable[SourceVideo]) -> Path:
        settings = self.settings
        path = settings.data_root / "sources.json"
        serializable = [json.loads(source.json()) for source in sources]
        path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def _parse_iso_duration(duration: str) -> int | None:
        total_seconds = 0
        current = ""
        units = {"H": 3600, "M": 60, "S": 1}
        for char in duration.replace("PT", ""):
            if char.isdigit():
                current += char
            elif char in units and current:
                total_seconds += int(current) * units[char]
                current = ""
        return total_seconds or None

    @staticmethod
    def _build_metrics(stats: dict) -> dict[str, float]:
        view_count = float(stats.get("viewCount", 0))
        like_count = float(stats.get("likeCount", 0))
        comment_count = float(stats.get("commentCount", 0))
        favorite_count = float(stats.get("favoriteCount", 0))
        velocity_score = math.log1p(view_count) + 0.5 * math.log1p(like_count + comment_count)
        engagement_rate = (like_count + comment_count) / max(view_count, 1)
        return {
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "favorite_count": favorite_count,
            "velocity_score": velocity_score,
            "engagement_rate": engagement_rate,
        }
