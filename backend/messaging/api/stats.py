from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_session
from ..models.conversation import Conversation
from ..models.message import Message
from ..models.buyer import Buyer

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_stats(session: AsyncSession = Depends(get_session)):
    """Get dashboard stats."""
    total_conversations = await session.scalar(
        select(func.count(Conversation.id))
    )
    active_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(Conversation.status == "active")
    )
    sold_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(Conversation.status == "sold")
    )
    total_messages = await session.scalar(select(func.count(Message.id)))
    total_buyers = await session.scalar(select(func.count(Buyer.id)))

    return {
        "total_conversations": total_conversations or 0,
        "active_conversations": active_conversations or 0,
        "sold_conversations": sold_conversations or 0,
        "total_messages": total_messages or 0,
        "total_buyers": total_buyers or 0,
    }
