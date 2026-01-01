import asyncio

from .pipeline import Pipeline
from .utils.logging import setup_logger

logger = setup_logger("main")


def main() -> None:
    pipeline = Pipeline()
    asyncio.run(pipeline.run())


if __name__ == "__main__":
    logger.info("Triggering single pipeline run")
    main()
