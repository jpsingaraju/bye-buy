"""Seed default listings and conversations into the database."""

import shutil
from pathlib import Path

from sqlalchemy import select, func

from .connection import async_session
from .models.listing import Listing

DEFAULT_LISTINGS = [
    {
        "title": "Airpod Pro 2nd Generation",
        "description": "Apple AirPods Pro 2nd Generation with MagSafe charging case. Great condition, fully functional with active noise cancellation.",
        "price": 120.0,
        "min_price": 90.0,
        "willing_to_negotiate": 0.3,
        "condition": "good",
        "status": "active",
        "seller_notes": "Delivery only, no local pickup. Looking for cash or Venmo. Includes original box and charging cable.",
    },
    {
        "title": "Home Office Chair [PERFECT CONDITION]",
        "description": "Home office chair in perfect condition. Ergonomic design, comfortable for long hours of work.",
        "price": 30.0,
        "min_price": 20.0,
        "willing_to_negotiate": 0.3,
        "condition": "like_new",
        "status": "active",
        "seller_notes": "Delivery only, no local pickup.",
    },
]


SEED_IMAGES = {
    "Airpod Pro 2nd Generation": ["airpods_1.jpg", "airpods_2.jpg"],
    "Home Office Chair [PERFECT CONDITION]": ["chair_1.jpg", "chair_2.jpg", "chair_3.jpg"],
}


async def seed_default_listings():
    """Insert default listings with images if they don't already exist."""
    from posting.models import ListingImage
    from posting.config import settings

    async with async_session() as db:
        for listing_data in DEFAULT_LISTINGS:
            result = await db.execute(
                select(Listing).where(Listing.title == listing_data["title"])
            )
            if result.scalar_one_or_none() is None:
                listing = Listing(**listing_data)
                db.add(listing)
                await db.flush()

                # Copy seed images from frontend/public/ to uploads/
                image_names = SEED_IMAGES.get(listing_data["title"], [])
                frontend_public = Path(__file__).parent.parent.parent / "frontend" / "public"
                upload_dir = settings.upload_dir
                upload_dir.mkdir(parents=True, exist_ok=True)

                for position, img_name in enumerate(image_names):
                    src = frontend_public / img_name
                    if src.exists():
                        dest = upload_dir / img_name
                        shutil.copy2(src, dest)
                        db.add(ListingImage(
                            listing_id=listing.id,
                            filename=img_name,
                            filepath=str(dest),
                            position=position,
                        ))
        await db.commit()


async def seed_default_conversations():
    """Insert demo buyers, conversations, and messages if none exist."""
    from messaging.models.buyer import Buyer
    from messaging.models.conversation import Conversation
    from messaging.models.message import Message

    async with async_session() as db:
        # Skip if conversations already exist
        count = await db.execute(select(func.count()).select_from(Conversation))
        if count.scalar() > 0:
            return

        # Get listings to link conversations to
        listings = (await db.execute(select(Listing))).scalars().all()
        listing_by_title = {l.title: l for l in listings}

        airpod = listing_by_title.get("Airpod Pro 2nd Generation")
        chair = listing_by_title.get("Home Office Chair [PERFECT CONDITION]")

        # Create buyers
        buyers = [
            Buyer(fb_name="Sarah Mitchell", fb_profile_url="https://facebook.com/sarah.mitchell"),
            Buyer(fb_name="Mike Rodriguez", fb_profile_url="https://facebook.com/mike.rodriguez"),
            Buyer(fb_name="James Kim", fb_profile_url="https://facebook.com/james.kim"),
            Buyer(fb_name="Lisa Thompson", fb_profile_url="https://facebook.com/lisa.thompson"),
            Buyer(fb_name="David Chen", fb_profile_url="https://facebook.com/david.chen"),
        ]
        for b in buyers:
            db.add(b)
        await db.flush()

        # Conversations for Airpod Pro
        convos = []
        if airpod:
            convos.append(Conversation(
                buyer_id=buyers[0].id, listing_id=airpod.id,
                fb_thread_id="thread_airpod_sarah", status="active",
                current_offer=100.0, last_message_at="2026-02-15T09:30:00",
            ))
            convos.append(Conversation(
                buyer_id=buyers[1].id, listing_id=airpod.id,
                fb_thread_id="thread_airpod_mike", status="agreed",
                agreed_price=110.0, current_offer=110.0,
                delivery_address="456 Oak Ave, Berkeley, CA",
                last_message_at="2026-02-15T08:00:00",
            ))

        # Conversations for Chair
        if chair:
            convos.append(Conversation(
                buyer_id=buyers[4].id, listing_id=chair.id,
                fb_thread_id="thread_chair_david", status="active",
                current_offer=25.0, last_message_at="2026-02-15T11:00:00",
            ))

        for c in convos:
            db.add(c)
        await db.flush()

        # Messages
        all_messages = []

        # Sarah -> Airpod Pro
        if len(convos) >= 1:
            cid = convos[0].id
            all_messages += [
                Message(conversation_id=cid, role="buyer", content="Hey, is this still available? The AirPods Pro 2nd gen?", sent_at="2026-02-13T10:15:00", delivered=True),
                Message(conversation_id=cid, role="seller", content="Yes! They are still available. They are in great condition with active noise cancellation working perfectly. Comes with the MagSafe charging case.", sent_at="2026-02-13T10:16:00", delivered=True),
                Message(conversation_id=cid, role="buyer", content="Nice! Would you take $85 for them?", sent_at="2026-02-13T10:20:00", delivered=True),
                Message(conversation_id=cid, role="seller", content="I appreciate the offer, but $85 is a bit low. The lowest I can go is $90. These retail for $249 new and they are in great shape.", sent_at="2026-02-13T10:21:00", delivered=True),
                Message(conversation_id=cid, role="buyer", content="How about $95? I can pick up today.", sent_at="2026-02-14T08:00:00", delivered=True),
                Message(conversation_id=cid, role="seller", content="I can do $100 since you are picking up today. That is my best price.", sent_at="2026-02-14T08:01:00", delivered=True),
                Message(conversation_id=cid, role="buyer", content="Let me think about it and get back to you.", sent_at="2026-02-15T09:30:00", delivered=True),
            ]

        # Mike -> Airpod Pro
        if len(convos) >= 2:
            cid = convos[1].id
            all_messages += [
                Message(conversation_id=cid, role="buyer", content="Hi there! Interested in the AirPods. What condition are they in?", sent_at="2026-02-12T14:00:00", delivered=True),
                Message(conversation_id=cid, role="seller", content="They are in great condition! Fully functional noise cancellation, comes with all ear tips and the original box. Battery health is excellent.", sent_at="2026-02-12T14:01:00", delivered=True),
                Message(conversation_id=cid, role="buyer", content="Sounds good. Can you do $100?", sent_at="2026-02-12T14:10:00", delivered=True),
                Message(conversation_id=cid, role="seller", content="I could meet you at $110. That is a great deal considering the condition and everything included.", sent_at="2026-02-12T14:11:00", delivered=True),
                Message(conversation_id=cid, role="buyer", content="Deal! $110 works. Can you ship to Berkeley?", sent_at="2026-02-13T09:00:00", delivered=True),
                Message(conversation_id=cid, role="seller", content="Absolutely! I will send you a payment link. Once confirmed, I will ship it out same day.", sent_at="2026-02-13T09:01:00", delivered=True),
                Message(conversation_id=cid, role="buyer", content="Payment sent! My address is 456 Oak Ave, Berkeley, CA.", sent_at="2026-02-15T08:00:00", delivered=True),
            ]

        # David -> Chair
        if len(convos) >= 3:
            cid = convos[2].id
            all_messages += [
                Message(conversation_id=cid, role="buyer", content="Hey! Is the office chair still available? Can you deliver to downtown?", sent_at="2026-02-14T11:30:00", delivered=True),
                Message(conversation_id=cid, role="seller", content="Yes it is! I can deliver within the area. It is in perfect condition, very comfortable for long work sessions.", sent_at="2026-02-14T11:31:00", delivered=True),
                Message(conversation_id=cid, role="buyer", content="Awesome. Would you take $20?", sent_at="2026-02-14T12:00:00", delivered=True),
                Message(conversation_id=cid, role="seller", content="I can do $25 with delivery included. That is a great deal for a chair in this condition.", sent_at="2026-02-14T12:01:00", delivered=True),
                Message(conversation_id=cid, role="buyer", content="$25 with delivery? That works for me! When can you drop it off?", sent_at="2026-02-15T11:00:00", delivered=True),
            ]

        for m in all_messages:
            db.add(m)
        await db.commit()
