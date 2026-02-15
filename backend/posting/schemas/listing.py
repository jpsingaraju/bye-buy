from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class ListingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    min_price: Optional[float] = Field(None, gt=0)
    willing_to_negotiate: float = Field(0.5, ge=0, le=1)
    seller_notes: Optional[str] = None
    condition: str = "good"
    location: Optional[str] = None


class ListingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)
    min_price: Optional[float] = Field(None, gt=0)
    willing_to_negotiate: Optional[float] = Field(None, ge=0, le=1)
    seller_notes: Optional[str] = None
    condition: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None


class ListingImageResponse(BaseModel):
    id: int
    listing_id: int
    filename: str
    filepath: str
    position: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ListingResponse(BaseModel):
    id: int
    title: str
    description: str
    price: float
    min_price: Optional[float] = None
    willing_to_negotiate: float = 0.5
    seller_notes: Optional[str] = None
    condition: str = "good"
    location: Optional[str] = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ListingWithImagesResponse(ListingResponse):
    images: list[ListingImageResponse] = []

    model_config = {"from_attributes": True}
