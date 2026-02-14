"""Navigate a Browserbase session to a login URL and keep it alive for manual auth."""

import asyncio
import sys
from playwright.async_api import async_playwright
from browserbase import Browserbase
from posting.config import settings

URLS = {
    "ebay": "https://signin.ebay.com/ws/eBayISAPI.dll?SignIn",
    "craigslist": "https://accounts.craigslist.org/login",
}

async def main():
    platform = sys.argv[1] if len(sys.argv) > 1 else ""
    url = URLS.get(platform)
    if not url:
        print(f"Usage: uv run python auth_login.py [{'|'.join(URLS)}]")
        sys.exit(1)

    bb = Browserbase(api_key=settings.browserbase_api_key)

    session = bb.sessions.create(
        project_id=settings.browserbase_project_id,
        browser_settings={
            "context": {
                "id": settings.browserbase_context_id,
                "persist": True,
            },
            "solve_captchas": True,
        },
    )
    session_id = session.id
    print(f"Session: {session_id}")

    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(session.connect_url)
    page = browser.contexts[0].pages[0]

    await page.goto(url, wait_until="domcontentloaded")
    await asyncio.sleep(2)
    print(f"Navigated to: {page.url}")

    debug_urls = bb.sessions.debug(session_id)
    print(f"\nOpen this URL to log in:\n{debug_urls.debugger_fullscreen_url}\n")
    print("Press Enter here AFTER you've logged in to save cookies and close session...")

    # Keep alive by waiting for input in a thread
    await asyncio.get_event_loop().run_in_executor(None, input)

    print(f"Final URL: {page.url}")
    await browser.close()
    await pw.stop()
    bb.sessions.update(session_id, status="REQUEST_RELEASE")
    print("Session closed. Cookies saved!")

if __name__ == "__main__":
    asyncio.run(main())
