import asyncio
import logging
from pathlib import Path

from playwright.async_api import async_playwright
from stagehand import AsyncStagehand

from .base import PlatformPoster, PostingResult
from .registry import PlatformRegistry
from ..config import settings

logger = logging.getLogger(__name__)

# Category mapping: keywords in listing title/description -> FB category path
# Each path is a list of exact text labels to click through the dropdown hierarchy
CATEGORY_PATHS = {
    "lamp": ["Home and kitchen", "Lamps and lighting"],
    "light": ["Home and kitchen", "Lamps and lighting"],
    "furniture": ["Furniture"],
    "sofa": ["Furniture", "Living room furniture", "Sofas, love seats and sectionals"],
    "table": ["Furniture", "Living room furniture", "Coffee tables"],
    "desk": ["Furniture", "Office furniture"],
    "chair": ["Furniture", "Living room furniture", "Living room chairs"],
    "bed": ["Furniture", "Bedroom furniture"],
    "phone": ["Mobile phones and accessories"],
    "laptop": ["Electronics"],
    "computer": ["Electronics"],
    "tv": ["Electronics"],
    "book": ["Books, films and music"],
    "clothing": ["Clothing, shoes and accessories"],
    "shirt": ["Clothing, shoes and accessories"],
    "shoes": ["Clothing, shoes and accessories"],
    "toy": ["Toys and games"],
    "garden": ["Patio and garden"],
    "tool": ["Tools and home improvement"],
    "kitchen": ["Home and kitchen", "Kitchen and dining"],
    "jewel": ["Jewellery & watches"],
    "watch": ["Jewellery & watches"],
    "instrument": ["Musical instruments"],
    "guitar": ["Musical instruments"],
    "sport": ["Sporting goods"],
    "bike": ["Sporting goods"],
}

# Default fallback category path
DEFAULT_CATEGORY_PATH = ["Miscellaneous"]

CONDITION_MAP = {
    "new": "New",
    "like_new": "Used – like new",
    "good": "Used – good",
    "fair": "Used – fair",
}


def _pick_category_path(title: str, description: str) -> list[str]:
    """Pick the best category path based on listing text."""
    text = f"{title} {description}".lower()
    for keyword, path in CATEGORY_PATHS.items():
        if keyword in text:
            return path
    return DEFAULT_CATEGORY_PATH


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
    ) -> PostingResult:
        """Post a listing to Facebook Marketplace.

        Uses Stagehand to create a Browserbase session with persistent
        Facebook login cookies, then Playwright for all DOM interactions.
        """
        client = None
        session_id = None
        pw = None

        try:
            # Initialize Stagehand (used only to create the Browserbase session)
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

            # Navigate to create listing page via Stagehand
            await client.sessions.navigate(
                id=session_id,
                url="https://www.facebook.com/marketplace/create/item",
            )
            await asyncio.sleep(3)

            # Connect Playwright via CDP for reliable DOM interaction
            pw = await async_playwright().start()
            browser = await pw.chromium.connect_over_cdp(cdp_url)
            page = browser.contexts[0].pages[0]

            # --- Step 1: Upload images ---
            if image_paths:
                file_payloads = []
                for p in image_paths:
                    path = Path(p)
                    if path.exists() and path.stat().st_size > 100:
                        suffix = path.suffix.lower()
                        mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else f"image/{suffix.lstrip('.')}"
                        file_payloads.append({
                            "name": path.name,
                            "mimeType": mime,
                            "buffer": path.read_bytes(),
                        })

                if file_payloads:
                    file_input = page.locator('input[type="file"][accept*="image"]').first
                    await file_input.set_input_files(file_payloads)
                    await page.wait_for_timeout(5000)
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

            # --- Step 4: Select category ---
            category_path = _pick_category_path(title, description)
            cat_input = page.locator('label:has-text("Category") input[role="combobox"]')
            await cat_input.click()
            await page.wait_for_timeout(2000)

            for level, cat_text in enumerate(category_path):
                clicked = await page.get_by_text(cat_text, exact=True).last.click()
                await page.wait_for_timeout(2000)
                logger.info(f"Category level {level}: {cat_text}")

            # Check if category was set (leaf node reached)
            cat_val = await cat_input.input_value()
            if not cat_val:
                # We're in a sub-menu but haven't reached a leaf.
                # Pick the first leaf option available.
                texts = await page.evaluate("""() => {
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
                }""")
                # Try to find a leaf node (one that will set the value)
                for item_text in texts:
                    if item_text in category_path or ">" in item_text or item_text == "Delivery available":
                        continue
                    await page.get_by_text(item_text, exact=True).last.click()
                    await page.wait_for_timeout(1500)
                    cat_val = await cat_input.input_value()
                    if cat_val:
                        logger.info(f"Category leaf: {cat_val}")
                        break

            if not cat_val:
                return PostingResult(
                    success=False,
                    error_message="Could not select a category",
                )

            # Dismiss any remaining dropdown
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)

            # --- Step 5: Select condition ---
            cond_text = CONDITION_MAP.get(condition, "Used – good")
            await page.locator('label:has-text("Condition")').first.click()
            await page.wait_for_timeout(1000)

            opts = page.locator('[role="option"]')
            for i in range(await opts.count()):
                text = await opts.nth(i).inner_text()
                if cond_text.lower() in text.lower() or text.lower() in cond_text.lower():
                    await opts.nth(i).click()
                    logger.info(f"Condition: {text}")
                    break
            await page.wait_for_timeout(500)

            # --- Step 6: Fill description ---
            desc_input = page.locator('label:has-text("Description") textarea')
            await desc_input.click()
            await desc_input.press_sequentially(description, delay=20)
            await page.keyboard.press("Tab")
            await page.wait_for_timeout(1000)

            # --- Step 7: Click Next ---
            next_btn = page.locator('div[aria-label="Next"]').first
            disabled = await next_btn.get_attribute("aria-disabled")
            if disabled == "true":
                return PostingResult(
                    success=False,
                    error_message="Next button disabled - form validation failed",
                )

            await next_btn.click()
            await page.wait_for_timeout(3000)
            logger.info("Clicked Next")

            # --- Step 8: Click Publish ---
            pub_btn = page.locator('div[aria-label="Publish"]').first
            await pub_btn.click()
            await page.wait_for_timeout(5000)
            logger.info("Clicked Publish")

            final_url = page.url
            success = "marketplace" in final_url and "create" not in final_url

            await browser.close()
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
