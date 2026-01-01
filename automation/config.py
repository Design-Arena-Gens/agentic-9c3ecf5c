import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Central configuration for the automation pipeline."""

    data_root: Path = Field(default_factory=lambda: Path(os.getenv("PIPELINE_DATA_ROOT", "data")))
    tmp_root: Path = Field(default_factory=lambda: Path(os.getenv("PIPELINE_TMP_ROOT", "tmp")))
    youtube_api_key: str | None = Field(default=None, env="YOUTUBE_API_KEY")
    youtube_client_secret_path: Path | None = Field(
        default=None, env="YOUTUBE_CLIENT_SECRET_PATH"
    )
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    replicate_api_token: str | None = Field(default=None, env="REPLICATE_API_TOKEN")
    ffmpeg_binary: str = Field(default=os.getenv("FFMPEG_BIN", "ffmpeg"))
    scheduler_cron: str = Field(default="0 12 * * *", env="PIPELINE_CRON")
    niche_filters: list[str] = Field(
        default_factory=lambda: [
            "motivation",
            "gaming",
            "podcast",
            "comedy",
            "facts",
            "ai",
            "finance",
        ]
    )
    prefer_languages: list[str] = Field(default_factory=lambda: ["en", "hi"])
    watermark_path: Path | None = Field(default=None, env="WATERMARK_PATH")
    brand_primary_hex: str = Field(default="#FF4D00")
    brand_secondary_hex: str = Field(default="#222222")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("data_root", "tmp_root", pre=True)
    def expand_path(cls, value: Path | str) -> Path:
        path = Path(value).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
