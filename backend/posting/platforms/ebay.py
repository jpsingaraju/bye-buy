import logging

from openai import AsyncOpenAI
from playwright.async_api import TimeoutError as PlaywrightTimeout

from .base import PlatformPoster, PostingResult
from .registry import PlatformRegistry
from ._helpers import (
    create_browserbase_session,
    ai_pick_category,
    validate_image_paths,
    detect_login_redirect,
)
from ..config import settings

logger = logging.getLogger(__name__)

CONDITION_MAP = {
    "new": "New",
    "like_new": "New other (see details)",
    "good": "Pre-owned",
    "fair": "Pre-owned",
}


@PlatformRegistry.register("ebay")
class EbayPoster(PlatformPoster):
    """Post listings to eBay using Browserbase + Playwright."""

    @property
    def platform_name(self) -> str:
        return "ebay"

    async def post_listing(
        self,
        title: str,
        description: str,
        price: float,
        image_paths: list[str],
        condition: str = "good",
    ) -> PostingResult:
        client = None
        session_id = None
        pw = None
        openai_client = AsyncOpenAI(api_key=settings.model_api_key)

        try:
            client, session_id, cdp_url, page, pw = await create_browserbase_session(
                url="https://www.ebay.com/sl/sell",
            )

            # --- Debug: screenshot for every attempt ---
            await page.screenshot(path="/tmp/ebay_debug.png")
            logger.info(f"eBay page URL: {page.url}")

            # --- Login detection ---
            login_err = detect_login_redirect(page, ["signin.ebay.com"])
            if login_err:
                return PostingResult(success=False, error_message=login_err)

            # The /sl/sell URL may show a landing page — click "Sell now" or
            # "List an item" to get to the actual form.
            try:
                sell_btn = page.locator('a:has-text("Sell now"), a:has-text("List an item"), button:has-text("Sell now"), button:has-text("List an item")').first
                await sell_btn.click(timeout=5000)
                await page.wait_for_timeout(3000)
                logger.info(f"Clicked sell button, now at: {page.url}")
                await page.screenshot(path="/tmp/ebay_debug2.png")
            except PlaywrightTimeout:
                logger.info("No 'Sell now' button found, may already be on form")

            # Check for login redirect after clicking sell
            login_err = detect_login_redirect(page, ["signin.ebay.com"])
            if login_err:
                return PostingResult(success=False, error_message=login_err)

            # --- Step 1: Enter title ("Tell us what you're selling") ---
            try:
                # eBay's quick listing tool has a search-style input
                title_input = page.locator('input[type="text"], input[type="search"], textarea').first
                await title_input.wait_for(timeout=10000)
                await title_input.click()
                await title_input.fill(title)
                await page.wait_for_timeout(500)
                logger.info(f"Entered title: {title}")
                await page.screenshot(path="/tmp/ebay_debug3.png")
            except PlaywrightTimeout:
                body_text = await page.text_content("body") or ""
                return PostingResult(
                    success=False,
                    error_message=f"eBay sell form not found. URL: {page.url}. Page text: {body_text[:300]}",
                )

            # Click search/continue/get started
            try:
                search_btn = page.locator('button:has-text("Search"), button:has-text("Continue"), button:has-text("Get started"), button[type="submit"]').first
                await search_btn.click(timeout=5000)
            except PlaywrightTimeout:
                await page.keyboard.press("Enter")
            await page.wait_for_timeout(4000)
            logger.info(f"After title submit, URL: {page.url}")
            await page.screenshot(path="/tmp/ebay_debug4.png")

            # --- Step 2: AI-powered category selection ---
            # eBay may show category suggestions or product matches
            try:
                await page.locator('[role="radio"], [role="option"], [role="listbox"], button:has-text("Select"), .category').first.wait_for(timeout=8000)

                # Extract all visible option/radio texts
                options_texts = await page.evaluate("""() => {
                    const items = [];
                    // Radio buttons and their labels
                    document.querySelectorAll('[role="radio"], [role="option"], label, .category-item, [data-testid*="category"]').forEach(el => {
                        const t = el.innerText?.trim();
                        if (t && t.length > 2 && t.length < 100 && !t.includes('\\n')) items.push(t);
                    });
                    return [...new Set(items)];
                }""")

                if options_texts:
                    logger.info(f"eBay category options ({len(options_texts)}): {options_texts[:10]}")
                    best_cat = await ai_pick_category(openai_client, title, description, options_texts, "eBay")
                    logger.info(f"eBay AI picked category: '{best_cat}'")
                    if best_cat:
                        try:
                            await page.get_by_text(best_cat, exact=False).first.click()
                            await page.wait_for_timeout(1000)
                        except Exception:
                            logger.warning(f"Could not click category '{best_cat}', clicking first option")
                            try:
                                await page.locator('[role="radio"], [role="option"]').first.click()
                            except Exception:
                                pass
                else:
                    logger.info("No category options found")
            except PlaywrightTimeout:
                logger.info("No category selection step found, continuing")

            # Click continue if present
            try:
                await page.locator('button:has-text("Continue"), button:has-text("Next")').first.click(timeout=3000)
                await page.wait_for_timeout(3000)
            except (PlaywrightTimeout, Exception):
                pass

            await page.screenshot(path="/tmp/ebay_debug5.png")
            logger.info(f"After category, URL: {page.url}")

            # --- Step 3: Upload images ---
            if image_paths:
                file_payloads = validate_image_paths(image_paths)
                if file_payloads:
                    try:
                        file_input = page.locator('input[type="file"]').first
                        await file_input.set_input_files(file_payloads)
                        await page.wait_for_timeout(5000)
                        logger.info(f"Uploaded {len(file_payloads)} image(s) to eBay")
                    except Exception as e:
                        logger.warning(f"Image upload failed: {e}")

            # --- Step 4: Select condition ---
            cond_text = CONDITION_MAP.get(condition, "Pre-owned")
            try:
                condition_el = page.locator('button:has-text("Condition"), select, [data-testid*="condition"], label:has-text("Condition")').first
                await condition_el.click(timeout=5000)
                await page.wait_for_timeout(500)
                await page.get_by_text(cond_text, exact=False).first.click()
                await page.wait_for_timeout(500)
                logger.info(f"eBay condition: {cond_text}")
            except (PlaywrightTimeout, Exception):
                logger.warning("Could not set condition, continuing with default")

            # --- Step 5: Set price ---
            try:
                price_input = page.locator('input[name*="price"], input[aria-label*="rice"], input[placeholder*="rice"], #price, input[id*="price"]').first
                await price_input.click(timeout=5000)
                await price_input.fill("")
                await price_input.fill(f"{price:.2f}")
                await page.wait_for_timeout(300)
                logger.info(f"eBay price: {price:.2f}")
            except (PlaywrightTimeout, Exception):
                logger.warning("Could not find price input")

            # --- Step 6: Fill description ---
            try:
                desc_input = page.locator('textarea, [contenteditable="true"], [role="textbox"]').first
                await desc_input.click(timeout=5000)
                await desc_input.fill(description)
                await page.wait_for_timeout(300)
                logger.info("eBay description filled")
            except (PlaywrightTimeout, Exception):
                logger.warning("Could not fill description")

            # --- Step 7: Set shipping to local pickup ---
            try:
                await page.get_by_text("Local pickup", exact=False).first.click(timeout=3000)
                logger.info("Set to local pickup")
            except (PlaywrightTimeout, Exception):
                logger.info("Could not set local pickup")

            await page.screenshot(path="/tmp/ebay_debug6.png")

            # --- Step 8: Click List it / Submit ---
            try:
                submit_btn = page.locator('button:has-text("List it"), button:has-text("List item"), button:has-text("Submit"), button:has-text("Publish")').first
                await submit_btn.click(timeout=5000)
                logger.info("Clicked eBay submit button")
            except PlaywrightTimeout:
                return PostingResult(
                    success=False,
                    error_message="Could not find eBay submit button",
                )

            # Wait for success
            await page.wait_for_timeout(5000)
            final_url = page.url
            await page.screenshot(path="/tmp/ebay_debug_final.png")

            success = "ebay.com" in final_url and "sell" not in final_url.split("?")[0]

            await page.context.browser.close()
            pw = None

            return PostingResult(
                success=success,
                external_url=final_url if success else None,
                error_message=None if success else f"eBay posting may have failed. Final URL: {final_url}",
            )

        except Exception as e:
            logger.exception("eBay posting failed")
            return PostingResult(success=False, error_message=str(e))
        finally:
            if pw:
                try:
                    await pw.stop()
                except Exception:
                    pass
            if client and session_id:
                try:
                    await client.sessions.end(id=session_id)
                except Exception:
                    pass
