from datetime import datetime
from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    sent_at: datetime
    delivered: bool

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
