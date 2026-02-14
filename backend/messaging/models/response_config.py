from sqlalchemy import String, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from database.connection import Base


class ResponseConfig(Base):
    __tablename__ = "response_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("listings.id"), nullable=True
    )
    system_prompt: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    auto_respond: Mapped[bool] = mapped_column(Boolean, default=True)
    max_response_delay_s: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )

    listing = relationship("Listing", lazy="selectin")
