from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class ListingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)


class ListingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)


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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ListingWithImagesResponse(ListingResponse):
    images: list[ListingImageResponse] = []

    model_config = {"from_attributes": True}
