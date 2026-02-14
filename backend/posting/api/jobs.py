from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from ..database.connection import get_session
from ..models import PostingJob, JobLog
from ..schemas import PostingJobResponse, PostingJobWithLogsResponse, JobLogResponse
from ..config import settings

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=PostingJobWithLogsResponse)
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)):
    """Get a job with its logs."""
    result = await session.execute(
        select(PostingJob).options(selectinload(PostingJob.logs)).where(PostingJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/logs", response_model=list[JobLogResponse])
async def get_job_logs(job_id: int, session: AsyncSession = Depends(get_session)):
    """Get logs for a job."""
    result = await session.execute(
        select(JobLog).where(JobLog.job_id == job_id).order_by(JobLog.created_at)
    )
    return result.scalars().all()


@router.post("/{job_id}/retry", response_model=PostingJobResponse)
async def retry_job(job_id: int, session: AsyncSession = Depends(get_session)):
    """Retry a failed job."""
    result = await session.execute(select(PostingJob).where(PostingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")

    if job.retry_count >= settings.max_retries:
        raise HTTPException(status_code=400, detail="Maximum retry count exceeded")

    job.status = "pending"
    job.error_message = None
    job.scheduled_at = datetime.utcnow()
    job.started_at = None
    job.completed_at = None

    await session.commit()
    await session.refresh(job)
    return job


@router.get("", response_model=list[PostingJobResponse])
async def list_jobs(
    status: str | None = None,
    listing_id: int | None = None,
    session: AsyncSession = Depends(get_session),
):
    """List all jobs with optional filtering."""
    query = select(PostingJob).order_by(PostingJob.scheduled_at.desc())

    if status:
        query = query.where(PostingJob.status == status)
    if listing_id:
        query = query.where(PostingJob.listing_id == listing_id)

    result = await session.execute(query)
    return result.scalars().all()
