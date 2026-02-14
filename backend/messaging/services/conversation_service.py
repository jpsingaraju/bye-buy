from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.conversation import Conversation
from ..models.message import Message


class ConversationService:
    @staticmethod
    async def get_all(
        session: AsyncSession,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """Get all conversations with optional status filter."""
        query = (
            select(Conversation)
            .options(selectinload(Conversation.buyer))
            .order_by(Conversation.last_message_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        if status:
            query = query.where(Conversation.status == status)

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
