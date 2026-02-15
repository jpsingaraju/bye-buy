from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.conversation import Conversation
from ..models.message import Message


class ConversationService:
    @staticmethod
    async def get_all(
        session: AsyncSession,
        status: str | None = None,
        listing_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """Get all conversations with optional status and listing_id filters."""
        query = (
            select(Conversation)
            .options(selectinload(Conversation.buyer))
            .order_by(Conversation.last_message_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        if status:
            query = query.where(Conversation.status == status)
        if listing_id is not None:
            query = query.where(Conversation.listing_id == listing_id)

        result = await session.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(
        session: AsyncSession, conversation_id: int
    ) -> Conversation | None:
        """Get a conversation with buyer, messages, and listing."""
        result = await session.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.buyer),
                selectinload(Conversation.messages),
                selectinload(Conversation.listing),
            )
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        buyer_id: int,
        listing_id: int | None = None,
        fb_thread_id: str | None = None,
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        query = select(Conversation).where(Conversation.buyer_id == buyer_id)
        if listing_id:
            query = query.where(Conversation.listing_id == listing_id)

        result = await session.execute(query)
        conversation = result.scalar_one_or_none()

        if conversation:
            return conversation

        conversation = Conversation(
            buyer_id=buyer_id,
            listing_id=listing_id,
            fb_thread_id=fb_thread_id,
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        return conversation

    @staticmethod
    async def update_status(
        session: AsyncSession, conversation_id: int, status: str
    ) -> Conversation | None:
        """Update conversation status."""
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return None

        conversation.status = status
        await session.commit()
        await session.refresh(conversation)
        return conversation

    @staticmethod
    async def save_deal_details(
        session: AsyncSession,
        conversation_id: int,
        agreed_price: float | None = None,
        delivery_address: str | None = None,
    ) -> Conversation | None:
        """Save deal details (agreed price and/or delivery address)."""
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return None
        if agreed_price is not None:
            conversation.agreed_price = agreed_price
        if delivery_address is not None:
            conversation.delivery_address = delivery_address
        await session.commit()
        await session.refresh(conversation)
        return conversation

    @staticmethod
    async def add_message(
        session: AsyncSession,
        conversation_id: int,
        role: str,
        content: str,
        delivered: bool = False,
    ) -> Message:
        """Add a message to a conversation and update last_message_at."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            delivered=delivered,
        )
        session.add(message)

        # Update conversation last_message_at
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.last_message_at = datetime.utcnow()

        await session.commit()
        await session.refresh(message)
        return message

    @staticmethod
    async def get_messages(
        session: AsyncSession,
        conversation_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """Get messages for a conversation."""
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sent_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_offer(
        session: AsyncSession, conversation_id: int, offer: float
    ) -> None:
        """Update current_offer to the buyer's latest offer."""
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return
        conversation.current_offer = offer
        await session.commit()

    @staticmethod
    async def get_competing_offer(
        session: AsyncSession, listing_id: int, exclude_conversation_id: int
    ) -> float | None:
        """Return the highest current_offer from other active conversations on the same listing."""
        result = await session.execute(
            select(func.max(Conversation.current_offer)).where(
                Conversation.listing_id == listing_id,
                Conversation.id != exclude_conversation_id,
                Conversation.status.in_(["active", "pending"]),
                Conversation.current_offer.isnot(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def close_competing_conversations(
        session: AsyncSession, listing_id: int, winning_conversation_id: int
    ) -> int:
        """Close all other active conversations on a listing when one buyer agrees."""
        result = await session.execute(
            select(Conversation).where(
                Conversation.listing_id == listing_id,
                Conversation.id != winning_conversation_id,
                Conversation.status.in_(["active"]),
            )
        )
        conversations = list(result.scalars().all())
        for conv in conversations:
            conv.status = "closed"
        await session.commit()
        return len(conversations)

    @staticmethod
    async def has_pending_deal(
        session: AsyncSession, listing_id: int
    ) -> bool:
        """Check if any conversation on this listing is in pending/confirmed status."""
        result = await session.execute(
            select(Conversation.id).where(
                Conversation.listing_id == listing_id,
                Conversation.status.in_(["pending", "confirmed"]),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def get_active_conversations(session: AsyncSession) -> list[Conversation]:
        """Get all active conversations with their messages and listings."""
        result = await session.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.buyer),
                selectinload(Conversation.messages),
                selectinload(Conversation.listing),
            )
            .where(Conversation.status == "active")
        )
        return list(result.scalars().all())
