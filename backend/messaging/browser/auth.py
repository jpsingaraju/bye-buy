import logging

from .client import get_stagehand_session

logger = logging.getLogger(__name__)


async def login_to_facebook() -> dict:
    """Open a headed browser to messenger.com for manual Facebook login.

    The user logs in manually. Cookies persist via userDataDir so subsequent
    sessions are already authenticated.
    """
    try:
        session = await get_stagehand_session()
        await session.navigate(url="https://www.messenger.com/marketplace")
        logger.info("Navigated to Messenger Marketplace — waiting for manual login")
        return {
            "status": "browser_open",
            "message": "Browser opened to Messenger. Please log in manually. "
            "Cookies will be saved for future sessions.",
        }
    except Exception as e:
        logger.error(f"Login error: {e}")
        return {"status": "error", "message": str(e)}
