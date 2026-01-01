from __future__ import annotations

import datetime as dt
from pathlib import Path

import google.oauth2.credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from ..config import get_settings
from ..data_models import RenderedShort
from ..utils.logging import setup_logger

logger = setup_logger("uploader")


class YouTubeUploader:
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.youtube_client_secret_path:
            raise RuntimeError("YOUTUBE_CLIENT_SECRET_PATH is required for uploads")
        self._service = None

    def _build_service(self):
        if self._service:
            return self._service
        credentials = google.oauth2.credentials.Credentials.from_authorized_user_file(
            str(self.settings.youtube_client_secret_path)
        )
        self._service = build("youtube", "v3", credentials=credentials)
        return self._service

    def upload(self, rendered: RenderedShort) -> RenderedShort:
        service = self._build_service()
        body = {
            "snippet": {
                "title": rendered.title,
                "description": rendered.description,
                "tags": rendered.hashtags,
                "categoryId": "24",  # Entertainment
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }
        if rendered.scheduled_time:
            body["status"]["privacyStatus"] = "private"
            body["status"]["publishAt"] = rendered.scheduled_time.isoformat()

        media = MediaFileUpload(str(rendered.output_path), chunksize=-1, resumable=True)
        try:
            request = service.videos().insert(part="snippet,status", body=body, media_body=media)
            response = request.execute()
        except HttpError as exc:
            logger.error("YouTube upload failed: %s", exc)
            raise
        rendered.youtube_video_id = response["id"]
        rendered.upload_status = "uploaded"
        logger.info("Uploaded short %s to YouTube as %s", rendered.output_path.name, response["id"])
        return rendered

    def schedule_best_time(self) -> dt.datetime:
        now = dt.datetime.utcnow()
        target_hour = 17  # 5 PM UTC -> convert to best audience
        next_slot = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        if next_slot < now:
            next_slot += dt.timedelta(days=1)
        return next_slot
