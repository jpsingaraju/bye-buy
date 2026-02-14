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
        await asyncio.sleep(4)
        return True
    except Exception as e:
        logger.error(f"Failed to navigate to marketplace inbox: {e}")
        return False


async def click_conversation(session, buyer_name: str) -> bool:
    """Click on a conversation in the Marketplace inbox.
    This opens a chat popup in the bottom right corner."""
    try:
        logger.info(f"Clicking conversation for '{buyer_name}'...")

        await session.act(
            input=(
                f"Click on the conversation row that contains the name "
                f"'{buyer_name}'. It is a button element in the main content "
                f"area of the Facebook Marketplace inbox."
            ),
        )

        await asyncio.sleep(4)
        logger.info(f"Clicked conversation for '{buyer_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to click conversation for {buyer_name}: {e}")
        return False


async def send_message(session, message: str) -> bool:
    """Type and send a message in the chat popup."""
    try:
        delay = random.uniform(5, 15)
        logger.info(f"Waiting {delay:.1f}s before typing (anti-detection)")
        await asyncio.sleep(delay)

        # Step 1: Click the input field and type the message
        await session.act(
            input=(
                f"Click on the message input field in the chat popup at the "
                f"bottom right of the screen and type this message: {message}"
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
