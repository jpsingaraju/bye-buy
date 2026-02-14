import asyncio
import logging
import random

logger = logging.getLogger(__name__)

MARKETPLACE_URL = "https://www.messenger.com/marketplace"


async def navigate_to_marketplace(session) -> bool:
    """Navigate to Messenger Marketplace if not already there."""
    try:
        await session.navigate(url=MARKETPLACE_URL)
        await asyncio.sleep(2)
        return True
    except Exception as e:
        logger.error(f"Failed to navigate to marketplace: {e}")
        return False


async def click_conversation(session, buyer_name: str) -> bool:
    """Click on a conversation in the sidebar by buyer name."""
    try:
        await session.execute(
            execute_options={
                "instruction": (
                    f"Click on the conversation with buyer named '{buyer_name}' "
                    "in the Messenger sidebar to open it."
                ),
                "max_steps": 3,
            },
            timeout=15.0,
        )
        await asyncio.sleep(1.5)
        return True
    except Exception as e:
        logger.error(f"Failed to click conversation for {buyer_name}: {e}")
        return False


async def send_message(session, message: str) -> bool:
    """Type and send a message in the currently open conversation."""
    try:
        # Random delay to seem human
        delay = random.uniform(5, 15)
        logger.info(f"Waiting {delay:.1f}s before typing (anti-detection)")
        await asyncio.sleep(delay)

        await session.execute(
            execute_options={
                "instruction": (
                    f"Type the following message in the message input box and send it "
                    f"(press Enter or click the send button):\n\n{message}"
                ),
                "max_steps": 5,
            },
            timeout=20.0,
        )
        await asyncio.sleep(1)
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False


async def go_back_to_conversation_list(session) -> bool:
    """Navigate back to the conversation list from an open conversation."""
    try:
        await session.execute(
            execute_options={
                "instruction": (
                    "Click the back arrow or button to return to the conversation "
                    "list / sidebar view."
                ),
                "max_steps": 3,
            },
            timeout=10.0,
        )
        await asyncio.sleep(1)
        return True
    except Exception as e:
        logger.error(f"Failed to go back: {e}")
        # Fallback: navigate directly
        return await navigate_to_marketplace(session)
