"""Open a Browserbase live session for manual authentication.

Usage:
    uv run python auth_session.py ebay
    uv run python auth_session.py craigslist

Log in manually in the browser window, then press Enter here to close the session
and persist cookies.
"""

import asyncio
import sys

from browserbase import Browserbase
from posting.config import settings


async def main():
    url = {
        "ebay": "https://signin.ebay.com/ws/eBayISAPI.dll?SignIn",
        "craigslist": "https://accounts.craigslist.org/login",
    }.get(sys.argv[1] if len(sys.argv) > 1 else "")

    if not url:
        print("Usage: uv run python auth_session.py [ebay|craigslist]")
        sys.exit(1)

    platform = sys.argv[1]
    bb = Browserbase(api_key=settings.browserbase_api_key)

    print(f"Creating Browserbase session for {platform} login...")
    session = bb.sessions.create(
        project_id=settings.browserbase_project_id,
        browser_settings={
            "context": {
                "id": settings.browserbase_context_id,
                "persist": True,
            },
        },
    )

    debug_urls = bb.sessions.debug(session.id)
    print(f"\nOpen this URL in your browser to log into {platform}:")
    print(f"  {debug_urls.debugger_fullscreen_url}")
    print(f"\nThe session will navigate to: {url}")
    print("Log in, then come back here and press Enter to save cookies.\n")

    input("Press Enter when done logging in...")

    print("Closing session (cookies will persist in the context)...")
    bb.sessions.update(session.id, status="REQUEST_RELEASE")
    print("Done! Cookies saved.")


if __name__ == "__main__":
    asyncio.run(main())
