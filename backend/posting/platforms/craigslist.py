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
    "new": "new",
    "like_new": "like new",
    "good": "good",
    "fair": "fair",
}


@PlatformRegistry.register("craigslist")
class CraigslistPoster(PlatformPoster):
    """Post listings to Craigslist using Browserbase + Playwright."""

    @property
    def platform_name(self) -> str:
        return "craigslist"

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
                url="https://post.craigslist.org/",
            )

            # --- Login detection ---
            login_err = detect_login_redirect(page, ["accounts.craigslist.org/login"])
            if login_err:
                return PostingResult(success=False, error_message=login_err)

            # --- Step 1: Select "for sale by owner" ---
            try:
                fso_radio = page.locator('input[value="fso"], label:has-text("for sale by owner")')
                await fso_radio.first.click(timeout=10000)
                await page.wait_for_timeout(500)

                # Click continue
                continue_btn = page.locator('button:has-text("continue"), button.pickbutton, input[type="submit"]').first
                await continue_btn.click(timeout=5000)
                await page.wait_for_timeout(2000)
                logger.info("Selected 'for sale by owner'")
            except PlaywrightTimeout:
                return PostingResult(
                    success=False,
                    error_message=f"Craigslist post form not found. Current URL: {page.url}",
                )

            # --- Step 2: AI-powered category selection ---
            try:
                await page.locator('input[type="radio"], label.selection-label').first.wait_for(timeout=8000)

                # Extract category radio label texts
                labels = await page.locator('label.selection-label, label:has(input[type="radio"])').all_text_contents()
                category_options = [t.strip() for t in labels if t.strip() and len(t.strip()) > 2]

                if category_options:
                    best_cat = await ai_pick_category(openai_client, title, description, category_options, "Craigslist")
                    logger.info(f"Craigslist AI picked category: '{best_cat}'")
                    if best_cat:
                        try:
                            await page.get_by_text(best_cat, exact=False).first.click()
                        except Exception:
                            logger.warning(f"Could not click category '{best_cat}', clicking first")
                            await page.locator('input[type="radio"]').first.click()
                else:
                    await page.locator('input[type="radio"]').first.click()

                await page.wait_for_timeout(500)
                continue_btn = page.locator('button:has-text("continue"), input[type="submit"]').first
                await continue_btn.click(timeout=5000)
                await page.wait_for_timeout(2000)
                logger.info("Category selected")
            except PlaywrightTimeout:
                logger.info("No category selection step, continuing")

            # --- Step 3: Fill listing form and submit ---
            # Craigslist may show validation errors on first load; fill and retry up to 2 times.
            for form_attempt in range(2):
                try:
                    title_input = page.locator('input[name="PostingTitle"]')
                    await title_input.wait_for(timeout=8000)
                    await title_input.fill(title)

                    price_input = page.locator('input[name="price"]')
                    await price_input.fill(str(int(price)))

                    desc_input = page.locator('textarea[name="PostingBody"]')
                    await desc_input.fill(description)

                    # ZIP code
                    if settings.craigslist_zip_code:
                        try:
                            zip_input = page.locator('input[name="postal"]')
                            await zip_input.fill(settings.craigslist_zip_code, timeout=3000)
                        except (PlaywrightTimeout, Exception):
                            pass

                    # Email
                    if settings.craigslist_email:
                        try:
                            email_input = page.locator('input[name="FromEMail"]')
                            await email_input.fill(settings.craigslist_email, timeout=3000)
                            try:
                                confirm_email = page.locator('input[name="ConfirmEMail"]')
                                await confirm_email.fill(settings.craigslist_email, timeout=2000)
                            except (PlaywrightTimeout, Exception):
                                pass
                        except (PlaywrightTimeout, Exception):
                            pass

                    # Condition
                    cond_value = CONDITION_MAP.get(condition, "good")
                    try:
                        cond_select = page.locator('select[name="condition"]')
                        await cond_select.select_option(label=cond_value, timeout=3000)
                    except (PlaywrightTimeout, Exception):
                        pass

                    await page.wait_for_timeout(500)
                    logger.info(f"Form filled (attempt {form_attempt + 1})")
                except PlaywrightTimeout:
                    return PostingResult(
                        success=False,
                        error_message=f"Craigslist form fields not found. Current URL: {page.url}",
                    )

                # Click continue to submit
                continue_btn = page.locator('button:has-text("continue"), input[type="submit"]').first
                await continue_btn.click(timeout=5000)
                await page.wait_for_timeout(3000)
                logger.info(f"After form submit (attempt {form_attempt + 1}), URL: {page.url}")

                # Check if we're still on the form with validation errors
                page_html = await page.content()
                page_text = await page.text_content("body") or ""
                if 'name="PostingTitle"' in page_html and "Some required information" in page_text:
                    logger.warning(f"Form validation failed (attempt {form_attempt + 1}), retrying...")
                    continue
                break

            # --- Step 4: Handle location/map page if shown ---
            for geo_attempt in range(3):
                current_url = page.url
                if "geoverify" not in current_url and "map" not in current_url:
                    break
                logger.info(f"On geoverify page (attempt {geo_attempt + 1})")
                try:
                    continue_btn = page.locator('button:has-text("continue"), input[type="submit"]').first
                    await continue_btn.click(timeout=5000)
                    await page.wait_for_timeout(3000)
                    logger.info(f"After geoverify, URL: {page.url}")
                except (PlaywrightTimeout, Exception):
                    break

            # --- Step 5: Upload images ---
            if image_paths:
                file_payloads = validate_image_paths(image_paths)
                if file_payloads:
                    try:
                        file_input = page.locator('input[type="file"]').first
                        await file_input.set_input_files(file_payloads)
                        await page.wait_for_timeout(5000)
                        logger.info(f"Uploaded {len(file_payloads)} image(s) to Craigslist")

                        # Click "done with images"
                        done_btn = page.locator('button:has-text("done with images"), a:has-text("done with images")').first
                        await done_btn.click(timeout=5000)
                        await page.wait_for_timeout(2000)
                    except (PlaywrightTimeout, Exception) as e:
                        logger.warning(f"Image upload issue: {e}")
            else:
                # No images — try to skip image page
                try:
                    done_btn = page.locator('button:has-text("done with images"), a:has-text("done with images")').first
                    await done_btn.click(timeout=3000)
                    await page.wait_for_timeout(2000)
                except (PlaywrightTimeout, Exception):
                    pass

            # Handle geoverify again in case it appears after images
            if "geoverify" in page.url:
                try:
                    continue_btn = page.locator('button:has-text("continue"), input[type="submit"]').first
                    await continue_btn.click(timeout=5000)
                    await page.wait_for_timeout(3000)
                except (PlaywrightTimeout, Exception):
                    pass

            # --- Step 6: Review and publish ---
            try:
                publish_btn = page.locator('button:has-text("publish"), input[value="publish"]').first
                await publish_btn.click(timeout=8000)
                logger.info("Clicked publish on Craigslist")
                await page.wait_for_timeout(5000)
            except PlaywrightTimeout:
                # May already be past the review page
                pass

            # --- Step 7: Handle email verification ---
            final_url = page.url
            page_text = await page.text_content("body") or ""

            if "check your email" in page_text.lower() or "email verification" in page_text.lower():
                return PostingResult(
                    success=True,
                    external_url=final_url,
                    error_message="Craigslist requires email verification. Check your email to complete the posting.",
                )

            # Success if we're past the posting flow (not on form/geoverify/edit pages)
            page_html = await page.content()
            success = (
                "craigslist.org" in final_url
                and "geoverify" not in final_url
                and "s=edit" not in final_url
                and 'name="PostingTitle"' not in page_html
            )

            await page.context.browser.close()
            pw = None

            return PostingResult(
                success=success,
                external_url=final_url if success else None,
                error_message=None if success else f"Craigslist posting may have failed. Final URL: {final_url}",
            )

        except Exception as e:
            logger.exception("Craigslist posting failed")
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
