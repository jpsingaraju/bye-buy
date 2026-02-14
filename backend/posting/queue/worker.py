import asyncio
import logging
from datetime import datetime
from sqlalchemy import select

from ..database.connection import async_session
from ..models import PostingJob
from ..config import settings
from .job_processor import process_job

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """Background worker that polls for pending jobs and processes them."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        """Start the background worker."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Background worker started")

    async def stop(self):
        """Stop the background worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Background worker stopped")

    async def _run(self):
        """Main worker loop."""
        while self._running:
            try:
                await self._process_pending_jobs()
            except Exception as e:
                logger.error(f"Worker error: {e}")

            await asyncio.sleep(settings.worker_poll_interval)

    async def _process_pending_jobs(self):
        """Process all pending jobs."""
        async with async_session() as session:
            # Get pending jobs ordered by scheduled time
            result = await session.execute(
                select(PostingJob)
                .where(PostingJob.status == "pending")
                .where(PostingJob.scheduled_at <= datetime.utcnow())
                .where(PostingJob.retry_count < settings.max_retries)
                .order_by(PostingJob.scheduled_at)
                .limit(5)  # Process up to 5 jobs at a time
            )
            jobs = result.scalars().all()

            for job in jobs:
                logger.info(f"Processing job {job.id} for platform {job.platform}")
                await process_job(session, job)


# Global worker instance
worker = BackgroundWorker()
