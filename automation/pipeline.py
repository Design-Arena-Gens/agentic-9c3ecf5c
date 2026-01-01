from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from .config import get_settings
from .data_models import PipelineResult, RenderedShort, SourceVideo, ViralSegment
from .services.analytics import AnalyticsTracker
from .services.collectors import TrendingCollector
from .services.downloader import VideoDownloader
from .services.editor import ShortRenderer
from .services.metadata import MetadataGenerator
from .services.segmenter import ViralSegmentDetector
from .services.transcript import TranscriptGenerator
from .services.uploader import YouTubeUploader
from .utils.logging import setup_logger

logger = setup_logger("pipeline")


class Pipeline:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.collector = TrendingCollector()
        self.downloader = VideoDownloader()
        self.transcript_generator = TranscriptGenerator()
        self.segmenter = ViralSegmentDetector()
        self.renderer = ShortRenderer()
        self.uploader = YouTubeUploader()
        self.analytics = AnalyticsTracker()

    async def run(self) -> list[PipelineResult]:
        logger.info("Starting pipeline run")
        sources = self.collector.fetch_youtube_trending(self.settings.niche_filters)
        tiktok, instagram = await asyncio.gather(
            self.collector.fetch_tiktok_trending(self.settings.niche_filters),
            self.collector.fetch_instagram_trending(self.settings.niche_filters),
        )
        sources.extend(tiktok)
        sources.extend(instagram)
        self.collector.persist_sources(sources)

        results: list[PipelineResult] = []
        for source in sources[:5]:
            try:
                result = await self._process_source(source)
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed processing %s: %s", source.id, exc)
        await self._persist_results(results)
        logger.info("Pipeline finished with %d results", len(results))
        return results

    async def _process_source(self, source: SourceVideo) -> PipelineResult:
        source = self.downloader.download(source)
        audio_path = await self.downloader.extract_audio(source)
        transcript_path = await self.transcript_generator.generate(source, audio_path)
        transcript_text = self.transcript_generator.load_transcript_text(transcript_path)

        segments = self.segmenter.detect_segments(source, transcript_text, audio_path)
        rendered_shorts = self._render_segments(source, segments)
        uploaded_shorts = self._upload_rendered(rendered_shorts)
        analytics_path = self.analytics.collect_metrics(uploaded_shorts)
        return PipelineResult(
            source=source,
            segments=segments,
            rendered_shorts=uploaded_shorts,
            analytics={"path": str(analytics_path)},
            completed_at=datetime.utcnow(),
        )

    def _render_segments(self, source: SourceVideo, segments: list[ViralSegment]) -> list[RenderedShort]:
        shorts = []
        for segment in segments[:2]:
            try:
                shorts.append(self.renderer.render(source, segment))
            except Exception as exc:  # noqa: BLE001
                logger.error("Render failed for segment %s: %s", segment.start_time, exc)
        return shorts

    def _upload_rendered(self, shorts: list[RenderedShort]) -> list[RenderedShort]:
        uploaded = []
        for short in shorts:
            if not short.output_path.exists():
                continue
            if short.scheduled_time is None:
                short.scheduled_time = self.uploader.schedule_best_time()
            try:
                uploaded.append(self.uploader.upload(short))
            except Exception as exc:  # noqa: BLE001
                logger.error("Upload failed: %s", exc)
        return uploaded

    async def _persist_results(self, results: list[PipelineResult]) -> Path:
        archive_dir = self.settings.data_root / "runs"
        archive_dir.mkdir(parents=True, exist_ok=True)
        path = archive_dir / f"run_{datetime.utcnow().isoformat()}.json"
        path.write_text(
            "[\n" + ",\n".join([result.json(indent=2) for result in results]) + "\n]",
            encoding="utf-8",
        )
        logger.info("Persisted run details to %s", path)
        return path
