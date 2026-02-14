"""Seed default listings into the database."""

from sqlalchemy import select

from .connection import async_session
from .models.listing import Listing

DEFAULT_LISTINGS = [
    {
        "title": "Airpod Pro 2nd Generation",
        "description": "Apple AirPods Pro 2nd Generation with MagSafe charging case. Great condition, fully functional with active noise cancellation.",
        "price": 120.0,
        "min_price": 90.0,
        "willing_to_negotiate": True,
        "condition": "good",
        "status": "active",
        "seller_notes": "Prefer local pickup. Looking for cash or Venmo. Includes original box and charging cable.",
    },
]


async def seed_default_listings():
    """Insert default listings if they don't already exist."""
    async with async_session() as db:
        for listing_data in DEFAULT_LISTINGS:
            result = await db.execute(
                select(Listing).where(Listing.title == listing_data["title"])
            )
            if result.scalar_one_or_none() is None:
                db.add(Listing(**listing_data))
        await db.commit()
