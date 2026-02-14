import logging
from pathlib import Path

from stagehand import Stagehand

from ..config import settings

logger = logging.getLogger(__name__)

CHROME_PROFILE_DIR = str(Path(__file__).parent.parent.parent / "chrome_profile")

_client: Stagehand | None = None
_session = None


async def get_stagehand_session():
    """Get or create a Stagehand session. Reuses a single browser session."""
    global _client, _session

    if _session is not None:
        return _session

    logger.info("Starting new Stagehand session (local mode)")
    _client = Stagehand(
        server="local",
        local_openai_api_key=settings.openai_api_key,
    )
    _session = await _client.sessions.start(
        model_name="openai/gpt-4o",
        browser={
            "type": "local",
            "launchOptions": {
                "headless": False,
                "userDataDir": CHROME_PROFILE_DIR,
                "preserveUserDataDir": True,
            },
        },
    )
    logger.info("Stagehand session started")
    return _session


async def close_session():
    """Close the current Stagehand session."""
    global _client, _session

    if _session:
        try:
            await _session.end()
            logger.info("Stagehand session closed")
        except Exception as e:
            logger.error(f"Error closing session: {e}")
        finally:
            _session = None
            _client = None
