from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from database.connection import get_session
from ..models import Listing, ListingImage, PostingJob
from ..schemas import (
    ListingCreate,
    ListingUpdate,
    ListingResponse,
    ListingWithImagesResponse,
    PostingJobCreate,
    PostingJobResponse,
)
from ..storage.images import image_storage

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", response_model=ListingWithImagesResponse)
async def create_listing(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    min_price: Optional[float] = Form(None),
    willing_to_negotiate: bool = Form(True),
    seller_notes: Optional[str] = Form(None),
    images: list[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_session),
):
    """Create a new listing with optional images."""
    listing = Listing(
        title=title,
        description=description,
        price=price,
        min_price=min_price,
        willing_to_negotiate=willing_to_negotiate,
        seller_notes=seller_notes,
    )
    session.add(listing)
    await session.flush()

    for position, image_file in enumerate(images):
        filename, filepath = await image_storage.save(image_file)
        listing_image = ListingImage(
            listing_id=listing.id,
            filename=filename,
            filepath=filepath,
            position=position,
        )
        session.add(listing_image)

    await session.commit()
    await session.refresh(listing, ["images"])
    return listing


@router.get("", response_model=list[ListingWithImagesResponse])
async def list_listings(session: AsyncSession = Depends(get_session)):
    """Get all listings with images."""
    result = await session.execute(
        select(Listing).options(selectinload(Listing.images)).order_by(Listing.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{listing_id}", response_model=ListingWithImagesResponse)
async def get_listing(listing_id: int, session: AsyncSession = Depends(get_session)):
    """Get a single listing by ID."""
    result = await session.execute(
        select(Listing).options(selectinload(Listing.images)).where(Listing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.put("/{listing_id}", response_model=ListingWithImagesResponse)
async def update_listing(
    listing_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    min_price: Optional[float] = Form(None),
    willing_to_negotiate: Optional[bool] = Form(None),
    seller_notes: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    images: list[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_session),
):
    """Update a listing."""
    result = await session.execute(
        select(Listing).options(selectinload(Listing.images)).where(Listing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if title is not None:
        listing.title = title
    if description is not None:
        listing.description = description
    if price is not None:
        listing.price = price
    if min_price is not None:
        listing.min_price = min_price
    if willing_to_negotiate is not None:
        listing.willing_to_negotiate = willing_to_negotiate
    if seller_notes is not None:
        listing.seller_notes = seller_notes
    if status is not None:
        listing.status = status

    # Add new images if provided
    if images:
        current_max_position = max((img.position for img in listing.images), default=-1)
        for i, image_file in enumerate(images):
            filename, filepath = await image_storage.save(image_file)
            listing_image = ListingImage(
                listing_id=listing.id,
                filename=filename,
                filepath=filepath,
                position=current_max_position + 1 + i,
            )
            session.add(listing_image)

    await session.commit()
    await session.refresh(listing, ["images"])
    return listing


@router.delete("/{listing_id}")
async def delete_listing(listing_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a listing and its images."""
    result = await session.execute(
        select(Listing).options(selectinload(Listing.images)).where(Listing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Delete image files
    for image in listing.images:
        await image_storage.delete(image.filepath)

    await session.delete(listing)
    await session.commit()
    return {"status": "deleted"}


@router.post("/{listing_id}/post", response_model=PostingJobResponse)
async def post_listing(
    listing_id: int,
    job_data: PostingJobCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a posting job for a listing."""
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    job = PostingJob(listing_id=listing_id, platform=job_data.platform)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job
