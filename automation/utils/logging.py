from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ..config import get_settings


def setup_logger(name: str = "pipeline") -> logging.Logger:
    settings = get_settings()
    log_dir = settings.data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(log_dir / f"{name}.log", maxBytes=5_000_000, backupCount=5)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s (%(filename)s:%(lineno)d)"
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger
