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


def _normalize_name(name: str) -> str:
    """Normalize a name for consistent DB matching.

    Lowercases, collapses whitespace, strips trailing periods.
    """
    name = name.lower().strip()
    name = " ".join(name.split())
    name = name.rstrip(".")
    return name


@dataclass
class ConversationPreview:
    """Preview of a conversation from the Marketplace inbox."""
    buyer_name: str          # normalized for DB matching
    display_name: str = ""   # original name for clicking in UI
    listing_title: str = ""
    preview_text: str = ""
    is_unread: bool = False  # whether the conversation row appears unread (bold/blue dot)


@dataclass
class ExtractedMessage:
    """A single message extracted from a conversation."""
    sender: str
    content: str
    is_from_buyer: bool = True


@dataclass
class ConversationData:
    """Full extracted data from a conversation thread."""
    buyer_name: str          # normalized for DB matching
    display_name: str = ""   # original name
    listing_title: str = ""
    messages: list[ExtractedMessage] = field(default_factory=list)


async def extract_conversation_list(session, max_retries: int = 2) -> list[ConversationPreview]:
    """Extract the list of conversations from the Facebook Marketplace inbox.

    Retries extraction a few times if the list comes back empty,
    since Facebook's inbox can take a moment to render.
    """
    import asyncio

    for attempt in range(max_retries):
        try:
            logger.info(f"[extract_conversation_list] Attempt {attempt + 1}/{max_retries}")
            result = await session.extract(
                instruction=(
                    "This is the Facebook Marketplace inbox page. There may be a list of "
                    "conversation rows on this page. IMPORTANT: If the list is empty or "
                    "still loading, return an empty list. Do NOT invent or fabricate any "
                    "conversations. If conversation rows ARE visible, each row contains: "
                    "the person's name (bold if unread), the listing/item title, and a "
                    "short message preview. Read the EXACT text displayed — copy the name, "
                    "listing title, and preview text character-for-character. Do NOT guess "
                    "or use placeholder names. If you cannot clearly read a row, skip it. "
                    "Mark is_unread as true if the name appears bold or there is an unread "
                    "indicator. Default is_unread to true if uncertain."
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
                                    "is_unread": {"type": "boolean"},
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
            logger.info(f"[extract_conversation_list] Raw extract result: {data}")
            conversations_raw = (
                data.get("conversations", []) if isinstance(data, dict) else []
            )

            if not conversations_raw and attempt < max_retries - 1:
                logger.info(f"[extract_conversation_list] Empty list (attempt {attempt + 1}/{max_retries}), waiting...")
                await asyncio.sleep(1.5)
                continue

            convos = [
                ConversationPreview(
                    buyer_name=_normalize_name(c.get("buyer_name", "Unknown")),
                    display_name=c.get("buyer_name", "Unknown"),
                    listing_title=c.get("listing_title", ""),
                    preview_text=c.get("preview_text", ""),
                    is_unread=c.get("is_unread", True),
                )
                for c in conversations_raw
            ]
            for c in convos:
                logger.info(
                    f"[extract_conversation_list] Conversation: name='{c.display_name}' "
                    f"(normalized='{c.buyer_name}'), listing='{c.listing_title}', "
                    f"preview='{c.preview_text[:60]}', unread={c.is_unread}"
                )
            logger.info(f"[extract_conversation_list] Total: {len(convos)} conversations")
            return convos
        except Exception as e:
            logger.error(f"Failed to extract conversation list: {e}")
            return []

    return []


async def extract_chat_messages(session, buyer_name: str = "", other_buyers: list[str] | None = None) -> ConversationData:
    """Extract messages from the open chat popup.

    Args:
        buyer_name: Display name of the expected buyer.
        other_buyers: Normalized names of other buyers in the inbox,
            used to filter out cross-talk from sidebar previews.
    """
    try:
        logger.info(f"[extract_chat_messages] Extracting messages for buyer_name='{buyer_name}'")
        buyer_hint = (
            f"There is an open chat popup window for a conversation with '{buyer_name}'. "
            if buyer_name
            else "There is an open chat popup window on the page. "
        )
        result = await session.extract(
            instruction=(
                f"{buyer_hint}"
                "Extract all actual chat messages from this popup. ONLY extract real "
                "messages sent by either the buyer or the seller. IGNORE all Facebook "
                "UI elements: quick reply buttons, 'Send a quick response' prompts, "
                "'Tap a response' text, scam warnings, 'Rate each other' prompts, "
                "'Message sent' confirmations, and any other interface text that is "
                "not a real chat message. For each message get: the sender's name, "
                "the message text, and whether it was sent by the buyer (not by "
                "me/the seller). Also get the buyer's name and the listing title "
                "shown in the popup."
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
        logger.info(f"[extract_chat_messages] Raw extract result: {data}")
        if not isinstance(data, dict):
            logger.warning(f"[extract_chat_messages] Result is not a dict: {type(data)}")
            return ConversationData(buyer_name="Unknown", listing_title="")

        raw_messages = data.get("messages", [])
        logger.info(f"[extract_chat_messages] Raw messages count: {len(raw_messages)}")
        for i, m in enumerate(raw_messages):
            filtered = _is_fb_ui_text(m.get("content", ""))
            logger.debug(
                f"[extract_chat_messages] Raw msg[{i}]: sender='{m.get('sender')}', "
                f"content='{m.get('content', '')[:80]}', is_from_buyer={m.get('is_from_buyer')}, "
                f"filtered_as_ui={filtered}"
            )

        # Filter out cross-talk: Stagehand sometimes picks up inbox sidebar
        # preview text from OTHER conversations and treats them as chat messages.
        # E.g., while reading Vikram's chat, it sees Anita's preview in the
        # sidebar and includes it as a "seller" message.
        expected_buyer_norm = _normalize_name(buyer_name) if buyer_name else None
        other_buyer_norms = set(other_buyers or [])
        messages = []
        for m in raw_messages:
            content = m.get("content", "")
            if not content or _is_fb_ui_text(content):
                continue
            sender = m.get("sender", "")
            sender_norm = _normalize_name(sender)
            is_from_buyer = m.get("is_from_buyer", True)

            # Drop if sender is a known OTHER buyer (cross-talk from sidebar)
            if other_buyer_norms and sender_norm in other_buyer_norms:
                logger.warning(
                    f"[extract_chat_messages] Dropping cross-talk from other buyer: "
                    f"sender='{sender}', content='{content[:60]}'"
                )
                continue

            # Drop if marked as buyer message but sender doesn't match expected buyer
            if is_from_buyer and expected_buyer_norm and sender_norm != expected_buyer_norm:
                logger.warning(
                    f"[extract_chat_messages] Dropping mismatched buyer message: "
                    f"sender='{sender}' (expected '{buyer_name}'), content='{content[:60]}'"
                )
                continue

            messages.append(
                ExtractedMessage(
                    sender=sender,
                    content=content,
                    is_from_buyer=is_from_buyer,
                )
            )

        raw_name = data.get("buyer_name", "Unknown")
        logger.info(
            f"[extract_chat_messages] Extracted: buyer='{raw_name}' "
            f"(normalized='{_normalize_name(raw_name)}'), "
            f"listing='{data.get('listing_title', '')}', "
            f"{len(messages)} messages (filtered {len(raw_messages) - len(messages)} UI texts)"
        )
        for i, msg in enumerate(messages):
            logger.info(
                f"[extract_chat_messages] msg[{i}]: sender='{msg.sender}', "
                f"from_buyer={msg.is_from_buyer}, content='{msg.content[:80]}'"
            )
        return ConversationData(
            buyer_name=_normalize_name(raw_name),
            display_name=raw_name,
            listing_title=data.get("listing_title", ""),
            messages=messages,
        )
    except Exception as e:
        logger.error(f"Failed to extract chat messages: {e}")
        return ConversationData(buyer_name="Unknown", listing_title="")
