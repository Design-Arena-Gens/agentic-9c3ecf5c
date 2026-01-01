from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import yt_dlp

from ..config import get_settings
from ..data_models import SourceVideo
from ..utils.logging import setup_logger

logger = setup_logger("downloader")


class VideoDownloader:
    def __init__(self) -> None:
        self.settings = get_settings()

    def download(self, video: SourceVideo) -> SourceVideo:
        output_dir = self.settings.data_root / "downloads" / video.platform.value
        output_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(output_dir / f"{video.id}.%(ext)s")

        ydl_opts = {
            "outtmpl": output_template,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "quiet": True,
            "noprogress": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video.url, download=True)
            filename = ydl.prepare_filename(info)
            if not filename.endswith(".mp4") and Path(f"{filename}.mp4").exists():
                filename = f"{filename}.mp4"
        downloaded_path = Path(filename).resolve()
        logger.info("Downloaded %s to %s", video.id, downloaded_path)
        video.downloaded_path = downloaded_path
        return video

    async def extract_audio(self, video: SourceVideo) -> Path:
        if not video.downloaded_path:
            raise ValueError("Video must be downloaded before extracting audio")
        audio_dir = self.settings.tmp_root / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"{video.id}.wav"
        args = [
            self.settings.ffmpeg_binary,
            "-i",
            str(video.downloaded_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(audio_path),
        ]
        process = await asyncio.create_subprocess_exec(*args)
        await process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg failed for {video.id}")
        return audio_path
