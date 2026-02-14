from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models import PostingJob, JobLog, Listing
from ..platforms.registry import PlatformRegistry
from ..config import settings


async def log_job(
    session: AsyncSession,
    job_id: int,
    level: str,
    message: str,
    screenshot_path: str | None = None,
):
    """Add a log entry for a job."""
    log = JobLog(
        job_id=job_id,
        level=level,
        message=message,
        screenshot_path=screenshot_path,
    )
    session.add(log)
    await session.commit()


async def process_job(session: AsyncSession, job: PostingJob) -> bool:
    """Process a single posting job.

    Args:
        session: Database session
        job: The job to process

    Returns:
        True if successful, False otherwise
    """
    # Update job status to posting
    job.status = "posting"
    job.started_at = datetime.utcnow()
    job.retry_count += 1
    await session.commit()

    await log_job(session, job.id, "info", f"Starting job for platform: {job.platform}")

    try:
        # Load the listing with images
        result = await session.execute(
            select(Listing)
            .options(selectinload(Listing.images))
            .where(Listing.id == job.listing_id)
        )
        listing = result.scalar_one_or_none()

        if not listing:
            job.status = "failed"
            job.error_message = "Listing not found"
            job.completed_at = datetime.utcnow()
            await session.commit()
            await log_job(session, job.id, "error", "Listing not found")
            return False

        # Get image paths
        image_paths = [img.filepath for img in listing.images]

        # Get the platform poster
        poster = PlatformRegistry.get_poster(job.platform)

        await log_job(
            session,
            job.id,
            "info",
            f"Posting listing '{listing.title}' to {job.platform}",
        )

        # Post the listing
        result = await poster.post_listing(
            title=listing.title,
            description=listing.description,
            price=listing.price,
            image_paths=image_paths,
            condition=listing.condition,
        )

        if result.success:
            job.status = "posted"
            job.external_id = result.external_id
            job.external_url = result.external_url
            job.completed_at = datetime.utcnow()
            await session.commit()
            await log_job(
                session,
                job.id,
                "info",
                f"Successfully posted. URL: {result.external_url or 'N/A'}",
            )
            return True
        else:
            job.status = "failed"
            job.error_message = result.error_message
            job.completed_at = datetime.utcnow()
            await session.commit()
            await log_job(session, job.id, "error", f"Failed: {result.error_message}")
            return False

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        await session.commit()
        await log_job(session, job.id, "error", f"Exception: {str(e)}")
        return False
