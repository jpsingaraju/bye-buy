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
    click_with_retry,
)
from ..config import settings

logger = logging.getLogger(__name__)

CONDITION_MAP = {
    "new": "New",
    "like_new": "Used – like new",
    "good": "Used – good",
    "fair": "Used – fair",
}


def _extract_dropdown_items_js() -> str:
    """JS to extract visible dropdown items from FB's overlay menus."""
    return """() => {
        const overlays = document.querySelectorAll('[style*="position: fixed"], [style*="position: absolute"]');
        const items = [];
        overlays.forEach(o => {
            if (o.offsetHeight > 100) {
                o.querySelectorAll('div').forEach(d => {
                    const t = d.innerText.trim();
                    if (d.offsetHeight > 10 && d.offsetHeight < 60 && t.length > 1 && !t.includes('\\n') && t.length < 60) {
                        items.push(t);
                    }
                });
            }
        });
        return [...new Set(items)];
    }"""


@PlatformRegistry.register("facebook_marketplace")
class FacebookMarketplacePoster(PlatformPoster):
    """Post listings to Facebook Marketplace using Browserbase + Playwright."""

    @property
    def platform_name(self) -> str:
        return "facebook_marketplace"

    async def post_listing(
        self,
        title: str,
        description: str,
        price: float,
        image_paths: list[str],
        condition: str = "good",
        location: str | None = None,
    ) -> PostingResult:
        """Post a listing to Facebook Marketplace."""
        client = None
        session_id = None
        pw = None
        openai_client = AsyncOpenAI(api_key=settings.model_api_key)

        try:
            client, session_id, cdp_url, page, pw = await create_browserbase_session(
                url="https://www.facebook.com/marketplace/create/item",
            )

            # --- Login detection ---
            login_err = detect_login_redirect(page, ["login", "checkpoint"])
            if login_err:
                return PostingResult(success=False, error_message=login_err)

            # Verify the create-listing form is present
            try:
                await page.locator('label:has-text("Title")').wait_for(timeout=10000)
            except PlaywrightTimeout:
                return PostingResult(
                    success=False,
                    error_message=f"Create listing form not found. Current URL: {page.url}",
                )

            # --- Step 1: Upload images ---
            if image_paths:
                file_payloads = validate_image_paths(image_paths)
                if file_payloads:
                    file_input = page.locator('input[type="file"][accept*="image"]').first
                    await file_input.set_input_files(file_payloads)
                    try:
                        await page.locator('div[role="img"], img[src*="blob:"], img[src*="scontent"]').first.wait_for(timeout=15000)
                    except PlaywrightTimeout:
                        await page.wait_for_timeout(3000)
                    logger.info(f"Uploaded {len(file_payloads)} image(s)")

            # --- Step 2: Fill title ---
            title_input = page.locator('label:has-text("Title") input')
            await title_input.click()
            await title_input.press_sequentially(title, delay=40)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(300)

            # --- Step 3: Fill price ---
            price_input = page.locator('label:has-text("Price") input')
            await price_input.click()
            await price_input.press_sequentially(str(int(price)), delay=40)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(300)

            # --- Step 4: AI-powered category selection ---
            cat_input = page.locator('label:has-text("Category") input[role="combobox"]')
            await cat_input.click()
            try:
                await page.locator('[role="option"], [role="listbox"]').first.wait_for(timeout=5000)
            except PlaywrightTimeout:
                await page.wait_for_timeout(2000)

            max_depth = 5
            for depth in range(max_depth):
                items = await page.evaluate(_extract_dropdown_items_js())
                filtered = [
                    t for t in items
                    if t not in ("Delivery available", "Category", "")
                    and ">" not in t
                    and len(t) > 1
                ]

                if not filtered:
                    break

                best = await ai_pick_category(openai_client, title, description, filtered, "Facebook Marketplace")
                logger.info(f"Category depth {depth}: AI picked '{best}' from {len(filtered)} options")

                if not best:
                    break

                clicked = await click_with_retry(page, best)
                if not clicked:
                    logger.warning(f"Could not click category '{best}'")
                    break

                await page.wait_for_timeout(1500)
                cat_val = await cat_input.input_value()
                if cat_val:
                    logger.info(f"Category leaf reached: {cat_val}")
                    break

            cat_val = await cat_input.input_value()
            if not cat_val:
                return PostingResult(
                    success=False,
                    error_message="Could not select a category",
                )

            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)

            # --- Step 5: Select condition ---
            cond_text = CONDITION_MAP.get(condition, "Used – good")
            await page.locator('label:has-text("Condition")').first.click()
            try:
                await page.locator('[role="option"]').first.wait_for(timeout=3000)
            except PlaywrightTimeout:
                await page.wait_for_timeout(1000)

            opts = page.locator('[role="option"]')
            for i in range(await opts.count()):
                text = await opts.nth(i).inner_text()
                if cond_text.lower() in text.lower() or text.lower() in cond_text.lower():
                    await opts.nth(i).click()
                    logger.info(f"Condition: {text}")
                    break
            await page.wait_for_timeout(300)

            # --- Step 6: Fill description ---
            desc_input = page.locator('label:has-text("Description") textarea')
            await desc_input.click()
            await desc_input.press_sequentially(description, delay=20)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(500)

            # --- Step 7: Click Next ---
            next_btn = page.locator('div[aria-label="Next"]').first
            disabled = await next_btn.get_attribute("aria-disabled")
            if disabled == "true":
                return PostingResult(
                    success=False,
                    error_message="Next button disabled - form validation failed",
                )

            await next_btn.click()
            try:
                await page.locator('div[aria-label="Publish"]').first.wait_for(timeout=10000)
            except PlaywrightTimeout:
                await page.wait_for_timeout(3000)
            logger.info("Clicked Next")

            # --- Step 8: Click Publish ---
            pub_btn = page.locator('div[aria-label="Publish"]').first
            await pub_btn.click()
            logger.info("Clicked Publish")

            try:
                await page.wait_for_url(
                    lambda url: "marketplace" in url and "create" not in url,
                    timeout=15000,
                )
            except PlaywrightTimeout:
                pass

            final_url = page.url
            success = "marketplace" in final_url and "create" not in final_url

            await page.context.browser.close()
            pw = None

            return PostingResult(
                success=success,
                external_url=final_url if success else None,
                error_message=None if success else f"Unexpected final URL: {final_url}",
            )

        except Exception as e:
            logger.exception("Facebook Marketplace posting failed")
            return PostingResult(
                success=False,
                error_message=str(e),
            )
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
