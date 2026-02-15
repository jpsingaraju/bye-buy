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
    "like_new": "Like new",
    "good": "Good",
    "fair": "Fair",
}


@PlatformRegistry.register("mercari")
class MercariPoster(PlatformPoster):
    """Post listings to Mercari using Browserbase + Playwright."""

    @property
    def platform_name(self) -> str:
        return "mercari"

    async def post_listing(
        self,
        title: str,
        description: str,
        price: float,
        image_paths: list[str],
        condition: str = "good",
        location: str | None = None,
    ) -> PostingResult:
        """Post a listing to Mercari."""
        client = None
        session_id = None
        pw = None
        openai_client = AsyncOpenAI(api_key=settings.model_api_key)

        try:
            client, session_id, cdp_url, page, pw = await create_browserbase_session(
                url="https://www.mercari.com/sell/",
            )

            # --- Login detection ---
            login_err = detect_login_redirect(page, ["login", "signup"])
            if login_err:
                return PostingResult(success=False, error_message=login_err)

            # Wait for the sell form to load
            try:
                await page.wait_for_selector('input[type="file"]', timeout=15000)
            except PlaywrightTimeout:
                return PostingResult(
                    success=False,
                    error_message=f"Sell form not found. Current URL: {page.url}",
                )

            # --- Step 1: Upload photos ---
            if image_paths:
                file_payloads = validate_image_paths(image_paths)
                if file_payloads:
                    file_input = page.locator('input[type="file"][accept*="image"]').first
                    await file_input.set_input_files(file_payloads)
                    await page.wait_for_timeout(3000)
                    logger.info(f"Uploaded {len(file_payloads)} image(s)")

            # --- Step 2: Fill title ---
            title_input = page.locator('input[name="name"], input[data-testid="name"]').first
            await title_input.click()
            await title_input.fill(title)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(300)
            logger.info("Filled title")

            # --- Step 3: Fill description ---
            desc_input = page.locator('textarea[name="description"], textarea[data-testid="description"]').first
            await desc_input.click()
            await desc_input.fill(description)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(300)
            logger.info("Filled description")

            # --- Step 4: Set price ---
            price_input = page.locator('input[name="price"], input[data-testid="price"]').first
            await price_input.click()
            await price_input.fill(str(int(price)))
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(300)
            logger.info(f"Set price to {int(price)}")

            # --- Step 5: Select condition ---
            cond_text = CONDITION_MAP.get(condition, "Good")
            try:
                cond_button = page.get_by_text(cond_text, exact=True).first
                await cond_button.click()
                await page.wait_for_timeout(500)
                logger.info(f"Selected condition: {cond_text}")
            except Exception:
                logger.warning(f"Could not select condition '{cond_text}', trying dropdown")
                try:
                    cond_dropdown = page.locator('select[name="condition"], [data-testid="condition"]').first
                    await cond_dropdown.select_option(label=cond_text)
                    logger.info(f"Selected condition via dropdown: {cond_text}")
                except Exception:
                    logger.warning("Could not select condition, continuing without it")

            # --- Step 6: Category selection (AI-powered) ---
            try:
                cat_button = page.locator('button:has-text("Category"), [data-testid="category"]').first
                await cat_button.click()
                await page.wait_for_timeout(1500)

                max_depth = 5
                for depth in range(max_depth):
                    options = await page.locator('[role="option"], [role="menuitem"], li[class*="category"], div[class*="category"] a, div[class*="category"] button').all_text_contents()
                    filtered = [t.strip() for t in options if t.strip() and len(t.strip()) > 1 and len(t.strip()) < 80]

                    if not filtered:
                        break

                    best = await ai_pick_category(openai_client, title, description, filtered, "Mercari")
                    logger.info(f"Category depth {depth}: AI picked '{best}' from {len(filtered)} options")

                    if not best:
                        break

                    clicked = await click_with_retry(page, best)
                    if not clicked:
                        logger.warning(f"Could not click category '{best}'")
                        break

                    await page.wait_for_timeout(1500)

                logger.info("Category selection completed")
            except Exception as e:
                logger.warning(f"Category selection failed: {e}, continuing")

            # --- Step 7: Shipping — select seller-paid prepaid label ---
            try:
                shipping_btn = page.locator('button:has-text("Shipping"), [data-testid="shipping"]').first
                await shipping_btn.click()
                await page.wait_for_timeout(1000)

                # Select prepaid label / seller pays shipping
                prepaid = page.get_by_text("Prepaid label", exact=False).first
                await prepaid.click()
                await page.wait_for_timeout(500)

                # Pick a default weight class (1 lb)
                weight_option = page.get_by_text("1 lb", exact=False).first
                try:
                    await weight_option.click(timeout=3000)
                    await page.wait_for_timeout(500)
                except PlaywrightTimeout:
                    logger.warning("Could not select weight class, using default")

                # Confirm / done
                try:
                    done_btn = page.locator('button:has-text("Done"), button:has-text("Save"), button:has-text("Update")').first
                    await done_btn.click(timeout=3000)
                    await page.wait_for_timeout(500)
                except PlaywrightTimeout:
                    pass

                logger.info("Shipping configured")
            except Exception as e:
                logger.warning(f"Shipping selection failed: {e}, continuing")

            # --- Step 8: Submit the listing ---
            submit_btn = page.locator('button:has-text("List"), button[data-testid="submit"]').first
            await submit_btn.click()
            logger.info("Clicked submit/list button")

            # Wait for navigation or confirmation
            try:
                await page.wait_for_url(
                    lambda url: "sell" not in url or "complete" in url or "success" in url,
                    timeout=15000,
                )
            except PlaywrightTimeout:
                await page.wait_for_timeout(3000)

            final_url = page.url
            success = "sell" not in final_url or "complete" in final_url or "success" in final_url

            await page.context.browser.close()
            pw = None

            return PostingResult(
                success=success,
                external_url=final_url if success else None,
                error_message=None if success else f"Unexpected final URL: {final_url}",
            )

        except Exception as e:
            logger.exception("Mercari posting failed")
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
