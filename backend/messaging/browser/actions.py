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


async def _activate_chat_system(session) -> None:
    """Click the Messenger chat bubble and close it to activate the chat system.
    Some accounts need this before chat popups will open."""
    try:
        logger.info("Activating chat system via Messenger bubble...")
        await session.act(
            input="Click the small circular Messenger chat icon in the bottom right corner of the page.",
        )
        await asyncio.sleep(1)
        await session.act(
            input="Close the Messenger chat panel that just opened.",
        )
        await asyncio.sleep(1)
        logger.info("Chat system activated")
    except Exception as e:
        logger.warning(f"Failed to activate chat system: {e}")


async def click_conversation(session, buyer_name: str) -> bool:
    """Click on a conversation in the Marketplace inbox.
    This opens a chat popup in the bottom right corner.
    If the popup doesn't open, activates the chat system and retries."""
    try:
        logger.info(f"Clicking conversation for '{buyer_name}'...")

        await session.act(
            input=(
                f"Click on the conversation row that contains the name "
                f"'{buyer_name}'. It is a button element in the main content "
                f"area of the Facebook Marketplace inbox."
            ),
        )

        await asyncio.sleep(2)

        # Check if chat popup opened
        try:
            result = await session.extract(
                instruction="Is there a chat popup open in the bottom right corner of the screen? Answer with just 'yes' or 'no'.",
                schema={"type": "object", "properties": {"popup_open": {"type": "string"}}, "required": ["popup_open"]},
            )
            popup_open = result.data.get("popup_open", "").lower() if hasattr(result, 'data') and isinstance(result.data, dict) else str(result.data).lower()
        except Exception:
            popup_open = "yes"  # assume it worked if we can't check

        if "no" in popup_open:
            logger.info("Chat popup didn't open, activating chat system and retrying...")
            await _activate_chat_system(session)
            await asyncio.sleep(1)

            # Retry clicking the conversation
            await session.act(
                input=(
                    f"Click on the conversation row that contains the name "
                    f"'{buyer_name}'. It is a button element in the main content "
                    f"area of the Facebook Marketplace inbox."
                ),
            )
            await asyncio.sleep(2)

        logger.info(f"Clicked conversation for '{buyer_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to click conversation for {buyer_name}: {e}")
        return False


async def send_message(session, message: str, buyer_name: str = "") -> bool:
    """Type and send a message in the chat popup."""
    try:
        delay = random.uniform(1, 3)
        logger.info(f"Waiting {delay:.1f}s before typing (anti-detection)")
        await asyncio.sleep(delay)

        # Step 1: Click the input field and type the message
        popup_ref = f" in {buyer_name}'s chat popup" if buyer_name else " in the chat popup at the bottom right of the screen"
        await session.act(
            input=(
                f"Click on the message input field{popup_ref} and type this message: {message}"
            ),
        )
        await asyncio.sleep(1)

        # Step 2: Press Enter to send the message
        await session.act(
            input="Press the Enter key to send the message that was just typed in the chat input field.",
        )
        await asyncio.sleep(1)
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False


async def close_all_chat_popups(session) -> bool:
    """Close all open chat popups at the bottom of the screen."""
    try:
        await session.act(
            input="Close ALL open chat popups at the bottom of the screen by clicking their X/close buttons. If there are no open chat popups, do nothing.",
        )
        await asyncio.sleep(1)
        return True
    except Exception as e:
        logger.warning(f"Failed to close all chat popups: {e}")
        return False


async def close_chat_popup(session) -> bool:
    """Close the chat popup."""
    try:
        await session.act(
            input="Click the X or close button on the chat popup header to close it.",
        )
        await asyncio.sleep(1)
        return True
    except Exception as e:
        logger.error(f"Failed to close chat popup: {e}")
        return False
