"""Shared helpers for platform posters (Browserbase, AI category picking, etc.)."""

import asyncio
import logging
from pathlib import Path

from openai import AsyncOpenAI
from playwright.async_api import async_playwright, Page
from stagehand import AsyncStagehand

from ..config import settings

logger = logging.getLogger(__name__)


async def create_browserbase_session(
    url: str,
) -> tuple[AsyncStagehand, str, str, Page, "async_playwright"]:
    """Create a Browserbase session, navigate to *url*, and return Playwright handles.

    Returns:
        (stagehand_client, session_id, cdp_url, page, playwright_instance)
    """
    client = AsyncStagehand(
        browserbase_api_key=settings.browserbase_api_key,
        browserbase_project_id=settings.browserbase_project_id,
        model_api_key=settings.model_api_key,
    )

    start_kwargs = {"model_name": "openai/gpt-4o"}
    if settings.browserbase_context_id:
        start_kwargs["browserbase_session_create_params"] = {
            "browser_settings": {
                "context": {
                    "id": settings.browserbase_context_id,
                    "persist": True,
                },
                "solve_captchas": True,
            }
        }

    resp = await client.sessions.start(**start_kwargs)
    session_id = resp.data.session_id
    cdp_url = resp.data.cdp_url
    logger.info(f"Browserbase session started: {session_id}")

    await client.sessions.navigate(id=session_id, url=url)
    await asyncio.sleep(3)

    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(cdp_url)
    page = browser.contexts[0].pages[0]

    return client, session_id, cdp_url, page, pw


async def ai_pick_category(
    openai_client: AsyncOpenAI,
    title: str,
    description: str,
    options: list[str],
    platform: str = "marketplace",
) -> str | None:
    """Use OpenAI to pick the best category from a list of options."""
    options_text = "\n".join(f"- {opt}" for opt in options)
    resp = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    f"You are a category classifier for {platform} listings. "
                    "Given a listing title, description, and a list of available categories, "
                    "return ONLY the exact name of the single best matching category. "
                    "Do not add quotes, explanations, or extra text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Listing title: {title}\n"
                    f"Listing description: {description}\n\n"
                    f"Available categories:\n{options_text}\n\n"
                    "Which category is the best match?"
                ),
            },
        ],
        temperature=0,
        max_tokens=100,
    )
    choice = resp.choices[0].message.content.strip()
    for opt in options:
        if opt.lower() == choice.lower():
            return opt
    for opt in options:
        if choice.lower() in opt.lower() or opt.lower() in choice.lower():
            return opt
    return choice


def validate_image_paths(image_paths: list[str]) -> list[dict]:
    """Check image paths exist and are > 100 bytes. Return Playwright file payloads."""
    payloads = []
    for p in image_paths:
        path = Path(p)
        if not path.exists():
            logger.warning(f"Image not found, skipping: {p}")
            continue
        if path.stat().st_size <= 100:
            logger.warning(f"Image too small ({path.stat().st_size} bytes), skipping: {p}")
            continue
        suffix = path.suffix.lower()
        mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else f"image/{suffix.lstrip('.')}"
        payloads.append({
            "name": path.name,
            "mimeType": mime,
            "buffer": path.read_bytes(),
        })
    return payloads


def detect_login_redirect(page: Page, keywords: list[str]) -> str | None:
    """Return an error string if the page URL contains any login keyword, else None."""
    current_url = page.url
    for kw in keywords:
        if kw in current_url:
            return f"Redirected to login page ({current_url}). Session cookies may have expired."
    return None


async def click_with_retry(page: Page, text: str, *, exact: bool = True, attempts: int = 2) -> bool:
    """Click an element matching *text* with retry. Returns True on success."""
    for attempt in range(attempts):
        try:
            await page.get_by_text(text, exact=exact).last.click()
            return True
        except Exception:
            if attempt < attempts - 1:
                logger.warning(f"Click failed for '{text}', retrying...")
                await page.wait_for_timeout(1000)
    return False
