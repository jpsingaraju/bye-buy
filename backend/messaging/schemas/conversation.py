from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from .message import MessageResponse


class BuyerResponse(BaseModel):
    id: int
    fb_name: str
    fb_profile_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ListingSummary(BaseModel):
    id: int
    title: str
    price: float
    min_price: Optional[float] = None
    status: str = "active"

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    buyer_id: int
    listing_id: Optional[int] = None
    fb_thread_id: Optional[str] = None
    status: str
    last_message_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    buyer: BuyerResponse
    messages: list[MessageResponse] = []
    listing: Optional[ListingSummary] = None

    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    status: Optional[str] = None
    listing_id: Optional[int] = None
