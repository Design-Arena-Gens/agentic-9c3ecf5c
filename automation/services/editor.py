from __future__ import annotations

from pathlib import Path

from moviepy.editor import AudioFileClip, CompositeAudioClip, CompositeVideoClip, TextClip, VideoFileClip
from moviepy.video.fx import all as vfx

from ..config import get_settings
from ..data_models import RenderedShort, SourceVideo, ViralSegment
from ..utils.logging import setup_logger
from .metadata import MetadataGenerator

logger = setup_logger("editor")


class ShortRenderer:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.metadata_generator = MetadataGenerator()

    def render(self, video: SourceVideo, segment: ViralSegment) -> RenderedShort:
        settings = self.settings
        if not video.downloaded_path:
            raise ValueError("Video must be downloaded before rendering")
        output_dir = settings.data_root / "shorts"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video.id}_{int(segment.start_time)}.mp4"

        clip = VideoFileClip(str(video.downloaded_path)).subclip(segment.start_time, segment.end_time)
        vertical_clip = self._convert_to_vertical(clip)
        vertical_clip = self._apply_zoom(vertical_clip)
        vertical_clip = self._apply_subtitles(vertical_clip, segment.transcript_snippet)
        vertical_clip = self._apply_branding(vertical_clip)

        audio = vertical_clip.audio
        background_music = self._load_background_music(segment)
        if background_music:
            audio = CompositeAudioClip([audio.volumex(1.0), background_music.volumex(0.15)])
        final_clip = vertical_clip.set_audio(audio)
        final_clip.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="medium",
            threads=4,
            verbose=False,
            logger=None,
        )
        clip.close()
        if background_music:
            background_music.close()
        final_clip.close()

        title, description, hashtags = self.metadata_generator.generate(segment, video)
        rendered = RenderedShort(
            segment=segment,
            output_path=output_path,
            title=title,
            description=description,
            hashtags=hashtags,
        )
        logger.info("Rendered short to %s", output_path)
        return rendered

    def _convert_to_vertical(self, clip: VideoFileClip) -> VideoFileClip:
        width, height = clip.size
        target_width = 1080
        target_height = 1920
        factor = max(target_height / height, target_width / width)
        clip = clip.resize(factor).crop(
            x_center=clip.w / 2,
            width=target_width,
            y_center=clip.h / 2,
            height=target_height,
        )
        return clip

    def _apply_zoom(self, clip: VideoFileClip) -> VideoFileClip:
        return clip.fx(vfx.resize, lambda t: 1 + 0.02 * t)

    def _apply_subtitles(self, clip: VideoFileClip, transcript: str) -> VideoFileClip:
        words = transcript.split()
        chunk_size = 4
        overlays = []
        for index in range(0, len(words), chunk_size):
            chunk = " ".join(words[index : index + chunk_size])
            start = index * 0.6
            duration = 1.6
            txt_clip = (
                TextClip(
                    chunk,
                    fontsize=72,
                    font="Arial-Bold",
                    color="white",
                    stroke_color="black",
                    stroke_width=4,
                )
                .set_start(start)
                .set_duration(duration)
                .set_pos(("center", 1400))
                .fadein(0.2)
                .fadeout(0.2)
            )
            overlays.append(txt_clip)
        return CompositeVideoClip([clip, *overlays])

    def _apply_branding(self, clip: VideoFileClip) -> VideoFileClip:
        settings = self.settings
        watermark_path = settings.watermark_path
        overlays = [clip]
        if watermark_path and Path(watermark_path).exists():
            logo = (
                VideoFileClip(str(watermark_path))
                .resize(height=120)
                .set_duration(clip.duration)
                .set_pos(("right", "top"))
                .set_opacity(0.6)
            )
            overlays.append(logo)
        cta = (
            TextClip(
                "Subscribe for more",
                fontsize=64,
                font="Arial-Bold",
                color=settings.brand_primary_hex,
            )
            .set_duration(clip.duration)
            .set_pos(("center", 1800))
        )
        overlays.append(cta)
        return CompositeVideoClip(overlays)

    def _load_background_music(self, segment: ViralSegment) -> AudioFileClip | None:
        music_dir = self.settings.data_root / "music"
        options = list(music_dir.glob("*.mp3"))
        if not options:
            return None
        target = options[hash(segment.source_video_id) % len(options)]
        return AudioFileClip(str(target))
