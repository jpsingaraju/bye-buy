import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConversationPreview:
    """Preview of a conversation from the sidebar."""
    buyer_name: str
    listing_title: str = ""
    is_unread: bool = False
    preview_text: str = ""


@dataclass
class ExtractedMessage:
    """A single message extracted from a conversation."""
    sender: str
    content: str
    is_from_buyer: bool = True


@dataclass
class ConversationData:
    """Full extracted data from a conversation thread."""
    buyer_name: str
    listing_title: str
    messages: list[ExtractedMessage] = field(default_factory=list)


async def extract_conversation_list(session) -> list[ConversationPreview]:
    """Extract the list of conversations from the Messenger sidebar."""
    try:
        result = await session.extract(
            instruction=(
                "Extract the list of conversations visible in the Messenger "
                "Marketplace sidebar. For each conversation, get: the buyer's name, "
                "the listing title (item name), whether it has an unread indicator "
                "(bold text, blue dot, or notification badge), and the preview text."
            ),
            schema={
                "type": "object",
                "properties": {
                    "conversations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "buyer_name": {"type": "string"},
                                "listing_title": {"type": "string"},
                                "is_unread": {"type": "boolean"},
                                "preview_text": {"type": "string"},
                            },
                        },
                    }
                },
            },
        )

        data = result.data if hasattr(result, "data") else result
        conversations_raw = (
            data.get("conversations", []) if isinstance(data, dict) else []
        )

        return [
            ConversationPreview(
                buyer_name=c.get("buyer_name", "Unknown"),
                listing_title=c.get("listing_title", ""),
                is_unread=c.get("is_unread", False),
                preview_text=c.get("preview_text", ""),
            )
            for c in conversations_raw
        ]
    except Exception as e:
        logger.error(f"Failed to extract conversation list: {e}")
        return []


async def extract_conversation_messages(session) -> ConversationData:
    """Extract all messages from the currently open conversation."""
    try:
        result = await session.extract(
            instruction=(
                "Extract all messages from this Messenger conversation. "
                "For each message, get: the sender's name, the message content, "
                "and whether it was sent by the buyer (not by me/the seller). "
                "Also extract the listing title from the conversation header."
            ),
            schema={
                "type": "object",
                "properties": {
                    "buyer_name": {"type": "string"},
                    "listing_title": {"type": "string"},
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sender": {"type": "string"},
                                "content": {"type": "string"},
                                "is_from_buyer": {"type": "boolean"},
                            },
                        },
                    },
                },
            },
        )

        data = result.data if hasattr(result, "data") else result
        if not isinstance(data, dict):
            return ConversationData(buyer_name="Unknown", listing_title="")

        messages = [
            ExtractedMessage(
                sender=m.get("sender", ""),
                content=m.get("content", ""),
                is_from_buyer=m.get("is_from_buyer", True),
            )
            for m in data.get("messages", [])
        ]

        return ConversationData(
            buyer_name=data.get("buyer_name", "Unknown"),
            listing_title=data.get("listing_title", ""),
            messages=messages,
        )
    except Exception as e:
        logger.error(f"Failed to extract messages: {e}")
        return ConversationData(buyer_name="Unknown", listing_title="")
