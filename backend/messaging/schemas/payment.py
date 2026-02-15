from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class TransactionResponse(BaseModel):
    id: int
    conversation_id: int
    listing_id: int
    buyer_id: int
    amount_cents: int
    stripe_checkout_session_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_transfer_id: Optional[str] = None
    checkout_url: Optional[str] = None
    tracking_number: Optional[str] = None
    status: str
    paid_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    paid_out_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrackingUpload(BaseModel):
    tracking_number: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    transaction_id: int
