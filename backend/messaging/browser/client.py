import logging

from stagehand import AsyncStagehand

from ..config import settings

logger = logging.getLogger(__name__)

_client: AsyncStagehand | None = None
_session = None


async def get_stagehand_session():
    """Get or create a Stagehand session via Browserbase."""
    global _client, _session

    if _session is not None:
        return _session

    logger.info("Starting new Stagehand session (Browserbase)")
    _client = AsyncStagehand(
        browserbase_api_key=settings.browserbase_api_key,
        browserbase_project_id=settings.browserbase_project_id,
        model_api_key=settings.model_api_key,
    )

    session_params = {
        "model_name": "gpt-4o",
    }

    if settings.browserbase_context_id:
        session_params["browserbase_session_create_params"] = {
            "browser_settings": {
                "context": {
                    "id": settings.browserbase_context_id,
                    "persist": True,
                },
                "solve_captchas": True,
            }
        }

    _session = await _client.sessions.start(**session_params)
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
