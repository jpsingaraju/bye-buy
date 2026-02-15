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
        await asyncio.sleep(0.5)
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


async def send_message(session, message: str, buyer_name: str = "") -> bool:
    """Type and send a message in the conversation panel.

    Args:
        session: Stagehand browser session.
        message: The message text to send.
        buyer_name: Name of the buyer whose chat we're sending to.
            Used to dismiss any other notification popups first.
    """
    try:
        # Dismiss any notification popups from OTHER conversations that may
        # have appeared while we were processing. These can steal focus and
        # cause the message to be typed into the wrong chat.
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
        logger.info(f"[send_message] Waiting {delay:.1f}s before typing, message='{message[:80]}...'")
        await asyncio.sleep(delay)

        buyer_hint = f" for the conversation with '{buyer_name}'" if buyer_name else ""
        logger.debug(f"[send_message] Typing message into chat{buyer_hint}...")
        type_result = await session.act(
            input=(
                f"Find the message input field (text box where you type a message) "
                f"in the chat panel{buyer_hint} and click on it. "
                f"Then type this message: {message}"
            ),
        )
        logger.debug(f"[send_message] type act() result: {type_result}")
        await asyncio.sleep(1)

        logger.debug("[send_message] Pressing Enter to send...")
        send_result = await session.act(
            input="Press the Enter key to send the message that was just typed.",
        )
        logger.debug(f"[send_message] enter act() result: {send_result}")
        await asyncio.sleep(1)
        logger.info("[send_message] Message sent successfully")
        return True
    except Exception as e:
        logger.error(f"[send_message] Failed: {e}")
        return False
