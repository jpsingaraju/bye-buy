import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

FB_UI_PATTERNS = [
    "send a quick response",
    "tap a response",
    "quick reply",
    "rate each other",
    "beware of common scams",
    "watch out for fake",
    "message sent",
    "you sent a quick reply",
    "payment apps",
    "report this conversation",
]


def _is_fb_ui_text(content: str) -> bool:
    lower = content.lower().strip()
    return any(p in lower for p in FB_UI_PATTERNS)


@dataclass
class ConversationPreview:
    """Preview of a conversation from the Marketplace inbox."""
    buyer_name: str
    listing_title: str = ""
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
    """Extract the list of conversations from the Facebook Marketplace inbox."""
    try:
        result = await session.extract(
            instruction=(
                "Extract ONLY the conversations that are literally visible on screen "
                "in the Facebook Marketplace inbox list. Do NOT make up or fabricate "
                "any names, titles, or text. If you cannot read a name clearly, skip "
                "that conversation. For each conversation get: the buyer's name, "
                "the listing/item title, and the message preview text."
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
                                "preview_text": {"type": "string"},
                            },
                        },
                    }
                },
            },
        )

        data = result.data if hasattr(result, "data") else result
        # Unwrap Data object: data.result contains the actual dict
        if hasattr(data, "result"):
            data = data.result
        logger.info(f"Raw extract result: {data}")
        conversations_raw = (
            data.get("conversations", []) if isinstance(data, dict) else []
        )

        convos = [
            ConversationPreview(
                buyer_name=c.get("buyer_name", "Unknown"),
                listing_title=c.get("listing_title", ""),
                preview_text=c.get("preview_text", ""),
            )
            for c in conversations_raw
        ]
        logger.info(f"Extracted {len(convos)} conversations")
        return convos
    except Exception as e:
        logger.error(f"Failed to extract conversation list: {e}")
        return []


async def extract_chat_messages(session) -> ConversationData:
    """Extract messages from the open chat/conversation on screen."""
    try:
        result = await session.extract(
            instruction=(
                "Extract chat messages from the open conversation popup/panel. "
                "ONLY extract actual messages that were sent by either the buyer "
                "or the seller. IGNORE all Facebook UI elements including: quick "
                "reply suggestion buttons, 'Send a quick response' prompts, "
                "'Tap a response to send' text, scam warning banners, 'Rate each "
                "other' prompts, 'Message sent' confirmations, and any other "
                "Facebook interface text that is not an actual chat message. "
                "For each real message get: the sender's name, the message text, "
                "and whether it was sent by the buyer (not by me/the seller). "
                "Also get the buyer's name and the listing title if visible."
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
        if hasattr(data, "result"):
            data = data.result
        if not isinstance(data, dict):
            return ConversationData(buyer_name="Unknown", listing_title="")

        messages = [
            ExtractedMessage(
                sender=m.get("sender", ""),
                content=m.get("content", ""),
                is_from_buyer=m.get("is_from_buyer", True),
            )
            for m in data.get("messages", [])
            if m.get("content") and not _is_fb_ui_text(m.get("content", ""))
        ]

        return ConversationData(
            buyer_name=data.get("buyer_name", "Unknown"),
            listing_title=data.get("listing_title", ""),
            messages=messages,
        )
    except Exception as e:
        logger.error(f"Failed to extract chat messages: {e}")
        return ConversationData(buyer_name="Unknown", listing_title="")
