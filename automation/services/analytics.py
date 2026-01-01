from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from googleapiclient.discovery import build

from ..config import get_settings
from ..data_models import RenderedShort
from ..utils.logging import setup_logger

logger = setup_logger("analytics")


class AnalyticsTracker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.service = None

    def _build_service(self):
        if self.service:
            return self.service
        if not self.settings.youtube_client_secret_path:
            raise RuntimeError("YOUTUBE_CLIENT_SECRET_PATH required for analytics")
        self.service = build(
            "youtubeAnalytics",
            "v2",
            developerKey=self.settings.youtube_api_key,
        )
        return self.service

    def collect_metrics(self, uploads: Iterable[RenderedShort]) -> Path:
        service = self._build_service()
        analytics_dir = self.settings.data_root / "analytics"
        analytics_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = analytics_dir / f"metrics_{datetime.utcnow().isoformat()}.json"
        snapshot = []
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=7)

        for rendered in uploads:
            if not rendered.youtube_video_id:
                continue
            response = (
                service.reports()
                .query(
                    ids="channel==MINE",
                    startDate=start_date.isoformat(),
                    endDate=end_date.isoformat(),
                    metrics="views,estimatedMinutesWatched,averageViewDuration,likes,shares",
                    filters=f"video=={rendered.youtube_video_id}",
                )
                .execute()
            )
            rows = response.get("rows", [[0, 0, 0, 0, 0]])[0]
            snapshot.append(
                {
                    "video_id": rendered.youtube_video_id,
                    "title": rendered.title,
                    "views": rows[0],
                    "minutes_watched": rows[1],
                    "avg_view_duration": rows[2],
                    "likes": rows[3],
                    "shares": rows[4],
                }
            )
        snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        logger.info("Persisted analytics snapshot to %s", snapshot_path)
        return snapshot_path
