from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .pipeline import Pipeline
from .utils.logging import setup_logger

logger = setup_logger("scheduler")


async def run_pipeline() -> None:
    pipeline = Pipeline()
    await pipeline.run()


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_pipeline, "cron", hour=12, minute=0, id="daily_pipeline")
    scheduler.start()
    logger.info("Scheduler started with daily pipeline job")
    return scheduler


def main() -> None:
    loop = asyncio.get_event_loop()
    scheduler = start_scheduler()
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler")
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
