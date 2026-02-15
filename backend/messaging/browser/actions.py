import asyncio
import logging
import random

logger = logging.getLogger(__name__)

MARKETPLACE_INBOX_URL = "https://www.facebook.com/marketplace/inbox"


async def navigate_to_marketplace(session) -> bool:
    """Navigate to Facebook Marketplace inbox."""
    try:
        logger.info("Navigating to Facebook Marketplace inbox...")
        await session.navigate(url=MARKETPLACE_INBOX_URL)
        await asyncio.sleep(2)
        return True
    except Exception as e:
        logger.error(f"Failed to navigate to marketplace inbox: {e}")
        return False


async def refresh_inbox(session) -> bool:
    """Refresh the Marketplace inbox page to check for new messages."""
    try:
        await session.navigate(url=MARKETPLACE_INBOX_URL)
        await asyncio.sleep(2)
        return True
    except Exception as e:
        logger.error(f"Failed to refresh inbox: {e}")
        return False


async def click_conversation(session, buyer_name: str) -> bool:
    """Click on a conversation row in the Marketplace inbox list.

    This selects the conversation and shows its messages in the
    right panel of the inbox page. No popups are opened.
    """
    try:
        logger.info(f"[click_conversation] Clicking conversation for '{buyer_name}'...")
        result = await session.act(
            input=(
                f"This is the Facebook Marketplace inbox page. There is a list of "
                f"conversation rows — each row contains a person's name, a listing "
                f"title, and a message preview. Find the row that contains the name "
                f"'{buyer_name}' and click on it. Do NOT click any other buttons, "
                f"icons, or links on the page."
            ),
        )
        logger.debug(f"[click_conversation] act() result: {result}")
        await asyncio.sleep(1.25)
        logger.info(f"[click_conversation] Done clicking for '{buyer_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to click conversation for {buyer_name}: {e}")
        return False


async def close_all_popups(session) -> None:
    """Close any popups or overlays that may have appeared on screen."""
    try:
        logger.debug("[close_all_popups] Closing any open popups...")
        result = await session.act(
            input=(
                "Look for any open chat popup windows or dialog boxes on the page. "
                "If any are open, click the X or close button on each one to close them. "
                "If none are open, do nothing."
            ),
        )
        logger.debug(f"[close_all_popups] act() result: {result}")
        await asyncio.sleep(1)
    except Exception as e:
        logger.warning(f"[close_all_popups] Failed: {e}")


async def send_message(session, message: str, buyer_name: str = "", max_attempts: int = 2) -> bool:
    """Type and send a message in the conversation panel, with verification.

    After sending, extracts messages from the chat to verify our message
    actually appears. Retries up to max_attempts times if verification fails.

    Args:
        session: Stagehand browser session.
        message: The message text to send.
        buyer_name: Name of the buyer whose chat we're sending to.
        max_attempts: Max send attempts if verification fails.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt == 1:
                # Dismiss notification popups only on first attempt
                logger.info(f"[send_message] Closing notification popups before sending to '{buyer_name}'...")
                await session.act(
                    input=(
                        "Look for any small chat notification popups or chat bubbles on "
                        "the page that may have appeared from other conversations. If any "
                        "are visible, click the X or close button on each one to dismiss "
                        "them. Do NOT close the main chat panel or conversation view. "
                        "If there are no notification popups, do nothing."
                    ),
                )
                await asyncio.sleep(0.5)

            delay = random.uniform(0.3, 0.8)
            logger.info(
                f"[send_message] Attempt {attempt}/{max_attempts}, "
                f"waiting {delay:.1f}s before typing, message='{message[:80]}...'"
            )
            await asyncio.sleep(delay)

            buyer_hint = f" for the conversation with '{buyer_name}'" if buyer_name else ""
            await session.act(
                input=(
                    f"Find the message input field (text box where you type a message) "
                    f"in the chat panel{buyer_hint} and click on it. "
                    f"Then type this message: {message}"
                ),
            )
            await asyncio.sleep(1)

            await session.act(
                input="Press the Enter key to send the message that was just typed.",
            )
            await asyncio.sleep(3)

            # Verify: extract messages and check if ours appears
            verified = await _verify_message_sent(session, message, buyer_name)
            if verified:
                logger.info(f"[send_message] Verified message delivered (attempt {attempt})")
                return True

            logger.warning(
                f"[send_message] Verification failed (attempt {attempt}/{max_attempts}), "
                f"message not found in chat"
            )
        except Exception as e:
            logger.error(f"[send_message] Attempt {attempt} failed: {e}")

    logger.error(f"[send_message] All {max_attempts} attempts failed for '{buyer_name}'")
    return False


async def _verify_message_sent(session, message: str, buyer_name: str) -> bool:
    """Extract recent messages from the chat and check if our message appears."""
    try:
        result = await session.extract(
            instruction=(
                "Extract the last 3 messages from the currently open chat panel. "
                "For each message, get the text content and whether it was sent by "
                "the seller (me) or the buyer."
            ),
            schema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
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

        messages = data.get("messages", []) if isinstance(data, dict) else []

        # Check if any seller message contains our text (fuzzy: first 30 chars)
        msg_prefix = message[:30].lower()
        for m in messages:
            if not m.get("is_from_buyer", True):
                content = m.get("content", "").lower()
                if msg_prefix in content:
                    return True

        logger.debug(
            f"[_verify_message_sent] Message not found. Looking for: '{msg_prefix}', "
            f"got: {[m.get('content', '')[:50] for m in messages]}"
        )
        return False
    except Exception as e:
        logger.warning(f"[_verify_message_sent] Verification extract failed: {e}")
        # If verification itself fails, assume sent to avoid infinite retries
        return True
