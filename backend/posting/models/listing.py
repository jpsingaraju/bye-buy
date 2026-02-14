from datetime import datetime
from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from ..database.connection import Base

if TYPE_CHECKING:
    from .image import ListingImage
    from .job import PostingJob


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    images: Mapped[list["ListingImage"]] = relationship(
        "ListingImage", back_populates="listing", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["PostingJob"]] = relationship(
        "PostingJob", back_populates="listing", cascade="all, delete-orphan"
    )
