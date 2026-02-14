from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_session
from ..schemas import (
    ConversationResponse,
    ConversationDetailResponse,
    ConversationUpdate,
    MessageResponse,
    MessageCreate,
)
from ..services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """List all conversations."""
    return await ConversationService.get_all(session, status=status, limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get conversation detail with messages."""
    conversation = await ConversationService.get_by_id(session, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """Get paginated messages for a conversation."""
    conversation = await ConversationService.get_by_id(session, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return await ConversationService.get_messages(
        session, conversation_id, limit=limit, offset=offset
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: int,
    message_data: MessageCreate,
    session: AsyncSession = Depends(get_session),
):
    """Manually send a message in a conversation."""
    conversation = await ConversationService.get_by_id(session, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message = await ConversationService.add_message(
        session,
        conversation_id=conversation_id,
        role="seller",
        content=message_data.content,
        delivered=False,
    )
    return message


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update_data: ConversationUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update conversation status or match to a listing."""
    conversation = await ConversationService.get_by_id(session, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if update_data.status:
        conversation.status = update_data.status
    if update_data.listing_id is not None:
        conversation.listing_id = update_data.listing_id

    await session.commit()
    await session.refresh(conversation)
    return conversation
