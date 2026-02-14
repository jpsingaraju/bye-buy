from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


VALID_PLATFORMS = {"facebook_marketplace", "ebay", "craigslist"}


class PostingJobCreate(BaseModel):
    platform: str = Field(..., pattern="^(facebook_marketplace|ebay|craigslist)$")


class BatchPostingJobCreate(BaseModel):
    platforms: list[str] = Field(..., min_length=1)

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_PLATFORMS
        if invalid:
            raise ValueError(f"Invalid platform(s): {', '.join(invalid)}")
        return v


class JobLogResponse(BaseModel):
    id: int
    job_id: int
    level: str
    message: str
    screenshot_path: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PostingJobResponse(BaseModel):
    id: int
    listing_id: int
    platform: str
    status: str
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PostingJobWithLogsResponse(PostingJobResponse):
    logs: list[JobLogResponse] = []

    model_config = {"from_attributes": True}
