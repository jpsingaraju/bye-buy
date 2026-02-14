from datetime import datetime
from sqlalchemy import String, Float, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from ..connection import Base


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    min_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    willing_to_negotiate: Mapped[bool] = mapped_column(Boolean, default=True)
    seller_notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    condition: Mapped[str] = mapped_column(String(20), default="good")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships are defined on the other side via backref:
    # - Listing.images  (added by ListingImage in posting/models/image.py)
    # - Listing.jobs     (added by PostingJob in posting/models/job.py)
