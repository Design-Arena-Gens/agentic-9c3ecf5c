from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import librosa
import numpy as np
import torch
from transformers import pipeline

from ..config import get_settings
from ..data_models import SourceVideo, ViralSegment
from ..utils.logging import setup_logger

logger = setup_logger("segmenter")


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


class ViralSegmentDetector:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.keyword_classifier = pipeline(
            "text-classification",
            model="facebook/bart-large-mnli",
            device=0 if torch.cuda.is_available() else -1,
        )

    def detect_segments(self, video: SourceVideo, transcript_text: str, audio_path: Path) -> list[ViralSegment]:
        energy_scores = self._sample_audio_energy(audio_path)
        transcript_segments = self._split_transcript(transcript_text)
        viral_segments: list[ViralSegment] = []

        for segment in transcript_segments:
            hook_score = self._score_hook(segment.text)
            energy_score = self._aggregate_energy(energy_scores, segment.start, segment.end)
            keywords = self._extract_keywords(segment.text)
            if hook_score + energy_score < 1.5:
                continue
            viral_segments.append(
                ViralSegment(
                    source_video_id=video.id,
                    start_time=segment.start,
                    end_time=segment.end,
                    hook_score=hook_score,
                    energy_score=energy_score,
                    keywords=keywords,
                    transcript_snippet=segment.text,
                )
            )
        viral_segments.sort(key=lambda s: (s.hook_score + s.energy_score), reverse=True)
        return viral_segments[:5]

    def _split_transcript(self, transcript_text: str) -> list[TranscriptSegment]:
        sentences = [s.strip() for s in transcript_text.split(".") if s.strip()]
        segments: list[TranscriptSegment] = []
        cursor = 0.0
        for sentence in sentences:
            duration = max(5.0, min(len(sentence.split()) * 0.6, 60.0))
            segments.append(TranscriptSegment(start=cursor, end=cursor + duration, text=sentence))
            cursor += duration * 0.9  # overlap to allow better segmentation
        return segments

    def _sample_audio_energy(self, audio_path: Path) -> np.ndarray:
        y, sr = librosa.load(audio_path, sr=16000)
        frame_length = 2048
        hop_length = 512
        energy = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        normalized = (energy - energy.min()) / (energy.max() - energy.min() + 1e-9)
        return normalized

    def _aggregate_energy(self, energy: np.ndarray, start: float, end: float) -> float:
        sr = 16000
        hop_length = 512
        frame_duration = hop_length / sr
        idx_start = int(start / frame_duration)
        idx_end = int(end / frame_duration)
        idx_end = min(idx_end, len(energy) - 1)
        window = energy[idx_start:idx_end] if idx_end > idx_start else energy[idx_start : idx_start + 1]
        score = float(np.mean(window))
        return math.sqrt(score)

    def _score_hook(self, text: str) -> float:
        prompt = f"This is the opening hook of a viral short: {text[:120]}"
        result = self.keyword_classifier(prompt, truncation=True)[0]
        score = result["score"]
        return float(score)

    def _extract_keywords(self, text: str) -> list[str]:
        doc = text.lower()
        keywords = [word.strip("#") for word in doc.split() if len(word) > 4]
        return list(dict.fromkeys(keywords))[:5]
