import logging

from playwright.async_api import TimeoutError as PlaywrightTimeout

from .base import PlatformPoster, PostingResult
from .registry import PlatformRegistry
from ._helpers import (
    create_browserbase_session,
    validate_image_paths,
    detect_login_redirect,
)
from ..config import settings

logger = logging.getLogger(__name__)

# Maps our condition values to eBay's "Confirm details" radio labels
CONDITION_MAP = {
    "new": "New",
    "like_new": "Open box",
    "good": "Used",
    "fair": "Used",
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
        location: str | None = None,
    ) -> PostingResult:
        client = None
        session_id = None
        pw = None

        try:
            client, session_id, cdp_url, page, pw = await create_browserbase_session(
                url="https://www.ebay.com/sl/sell",
            )

            await page.screenshot(path="/tmp/ebay_debug1.png")
            logger.info(f"eBay page URL: {page.url}")

            # --- Login detection ---
            login_err = detect_login_redirect(page, ["signin.ebay.com"])
            if login_err:
                return PostingResult(success=False, error_message=login_err)

            # --- Step 1: Click "Sell now" on landing page ---
            try:
                sell_btn = page.locator(
                    'a:has-text("Sell now"), button:has-text("Sell now"), '
                    'a:has-text("List an item"), button:has-text("List an item")'
                ).first
                await sell_btn.click(timeout=5000)
                await page.wait_for_timeout(3000)
                logger.info(f"Clicked sell button, now at: {page.url}")
            except PlaywrightTimeout:
                logger.info("No 'Sell now' button, may already be on form")

            # Check for login redirect after clicking sell
            login_err = detect_login_redirect(page, ["signin.ebay.com"])
            if login_err:
                return PostingResult(success=False, error_message=login_err)

            # --- Step 2: Enter title and search ---
            try:
                title_input = page.locator(
                    'input[type="text"], input[type="search"], input[placeholder*="Tell us"]'
                ).first
                await title_input.wait_for(timeout=10000)
                await title_input.click()
                await title_input.fill(title)
                await page.wait_for_timeout(1000)
                logger.info(f"Entered title: {title}")
            except PlaywrightTimeout:
                body_text = await page.text_content("body") or ""
                return PostingResult(
                    success=False,
                    error_message=f"eBay title input not found. URL: {page.url}. Text: {body_text[:300]}",
                )

            # Dismiss autocomplete and click the search button
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(500)

            try:
                search_btn = page.locator('button[type="submit"], button[aria-label="Search"]').first
                await search_btn.click(timeout=5000)
                logger.info("Clicked search button")
            except PlaywrightTimeout:
                await title_input.press("Enter")
                logger.info("Pressed Enter to search")

            await page.wait_for_timeout(5000)
            logger.info(f"After title search, URL: {page.url}")

            # --- Step 3: "Find a match" page ---
            # Click the first product match, or "Continue without match"
            try:
                await page.locator('text=Find a match').first.wait_for(timeout=8000)
                logger.info("On 'Find a match' page")

                # Try clicking the first product card
                product_clicked = False
                try:
                    # Product cards are typically clickable divs/links with images
                    product_cards = page.locator('[data-testid*="product"], [class*="product"], a:has(img)').first
                    await product_cards.click(timeout=3000)
                    product_clicked = True
                    logger.info("Clicked first product match")
                    await page.wait_for_timeout(2000)
                except (PlaywrightTimeout, Exception):
                    pass

                if not product_clicked:
                    # Click "Continue without match"
                    try:
                        await page.get_by_text("Continue without match", exact=False).first.click(timeout=3000)
                        logger.info("Clicked 'Continue without match'")
                        await page.wait_for_timeout(2000)
                    except (PlaywrightTimeout, Exception):
                        logger.warning("Could not click product or continue without match")
            except PlaywrightTimeout:
                logger.info("No 'Find a match' page, continuing")

            # --- Step 3b: Handle Category selection modal ---
            # eBay sometimes shows a "Category" picker after product selection.
            # Click the first suggested category and then "Done".
            try:
                cat_heading = page.locator('text=Category').first
                await cat_heading.wait_for(timeout=5000)
                # Check we're actually on a category modal (not just any "Category" text)
                if await page.locator('text=Suggested').first.is_visible(timeout=2000):
                    logger.info("Category selection modal appeared")

                    # Click the first suggested category link
                    try:
                        first_suggestion = page.locator('text=Cell Phones').first
                        await first_suggestion.click(timeout=3000)
                        logger.info("Clicked first suggested category")
                        await page.wait_for_timeout(1000)
                    except (PlaywrightTimeout, Exception):
                        # Try clicking any link under "Suggested"
                        try:
                            suggested_link = page.locator('[class*="suggestion"], [class*="Suggested"] >> a, [class*="category"] >> a').first
                            await suggested_link.click(timeout=2000)
                            logger.info("Clicked suggested category link")
                            await page.wait_for_timeout(1000)
                        except (PlaywrightTimeout, Exception):
                            logger.warning("Could not click suggested category")

                    # Click "Done" button
                    try:
                        done_btn = page.get_by_text("Done", exact=True).first
                        await done_btn.click(timeout=3000)
                        logger.info("Clicked Done on category modal")
                        await page.wait_for_timeout(3000)
                    except (PlaywrightTimeout, Exception):
                        logger.warning("Could not click Done on category modal")
            except (PlaywrightTimeout, Exception):
                logger.info("No category modal, continuing")

            # --- Step 4: "Confirm details" condition modal ---
            cond_text = CONDITION_MAP.get(condition, "Used")
            try:
                await page.locator('text=Confirm details').first.wait_for(timeout=8000)
                logger.info("Condition modal appeared")

                # Click condition using get_by_text (matches eBay's custom radio labels)
                condition_selected = False
                for label in [cond_text, "Used", "Open box", "New"]:
                    try:
                        await page.get_by_text(label, exact=True).first.click(timeout=2000)
                        condition_selected = True
                        logger.info(f"Selected condition: {label}")
                        break
                    except (PlaywrightTimeout, Exception):
                        continue

                if not condition_selected:
                    # JS fallback: find and click the radio by its sibling text
                    try:
                        await page.evaluate("""(condText) => {
                            const radios = document.querySelectorAll('input[type="radio"]');
                            for (const radio of radios) {
                                const parent = radio.closest('div, label, li');
                                if (parent && parent.textContent.includes(condText)) {
                                    radio.click();
                                    return true;
                                }
                            }
                            // Fallback: click the third radio ("Used")
                            if (radios.length >= 3) { radios[2].click(); return true; }
                            if (radios.length > 0) { radios[0].click(); return true; }
                            return false;
                        }""", cond_text)
                        logger.info(f"Selected condition via JS: {cond_text}")
                        condition_selected = True
                    except Exception as e:
                        logger.warning(f"JS condition click failed: {e}")

                await page.wait_for_timeout(1000)

                # Click "Continue to listing"
                try:
                    continue_btn = page.get_by_text("Continue to listing", exact=False).first
                    await continue_btn.click(timeout=5000)
                    logger.info("Clicked 'Continue to listing'")
                    await page.wait_for_timeout(5000)
                except PlaywrightTimeout:
                    # Try clicking any button at the bottom of the modal
                    try:
                        await page.locator('button:has-text("Continue")').first.click(timeout=3000)
                        logger.info("Clicked Continue button")
                        await page.wait_for_timeout(5000)
                    except PlaywrightTimeout:
                        logger.warning("Could not click 'Continue to listing'")

            except PlaywrightTimeout:
                logger.info("No condition modal, continuing")

            await page.screenshot(path="/tmp/ebay_debug6.png")
            logger.info(f"After condition, URL: {page.url}")

            # --- Step 5: Full listing editor ---
            # eBay's "Complete your listing" page with sections:
            # Photos, Title, Category, Item Specifics, Condition,
            # Description, Pricing/Format, Shipping, then "List it".
            await page.wait_for_timeout(3000)

            # Dismiss any popups (photo tips, etc.)
            for _ in range(3):
                try:
                    close_btn = page.locator(
                        'button[aria-label="Close"], button:has-text("Got it"), '
                        'button:has-text("No thanks"), [data-testid="close"]'
                    ).first
                    await close_btn.click(timeout=1500)
                    await page.wait_for_timeout(500)
                except (PlaywrightTimeout, Exception):
                    break

            await page.screenshot(path="/tmp/ebay_debug7.png")

            # Upload photos if available
            if image_paths:
                file_payloads = validate_image_paths(image_paths)
                if file_payloads:
                    try:
                        file_input = page.locator('input[type="file"]').first
                        await file_input.set_input_files(file_payloads)
                        await page.wait_for_timeout(5000)
                        logger.info(f"Uploaded {len(file_payloads)} image(s)")
                    except Exception as e:
                        logger.warning(f"Image upload failed: {e}")

            # --- Change format to Buy It Now FIRST (changes the pricing UI) ---
            # eBay uses a custom listbox component. The <select name="format"> is hidden
            # (class="listbox__native"). We must interact with the VISIBLE custom dropdown.
            try:
                # Scroll to pricing section
                await page.evaluate("""() => {
                    const el = document.querySelector('select[name="format"]');
                    if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
                }""")
                await page.wait_for_timeout(500)

                cur_val = await page.evaluate("() => document.querySelector('select[name=\"format\"]')?.value || 'N/A'")
                logger.info(f"Current format value: {cur_val}")

                # Debug: log the DOM structure around the format select
                format_html = await page.evaluate("""() => {
                    const sel = document.querySelector('select[name="format"]');
                    if (!sel) return 'no select found';
                    let el = sel.parentElement;
                    for (let i = 0; i < 3 && el?.parentElement; i++) el = el.parentElement;
                    return el ? el.outerHTML.substring(0, 1500) : 'no parent';
                }""")
                logger.info(f"Format DOM: {format_html}")

                format_changed = False

                # Strategy 1: Click the listbox button to open dropdown, then click option
                # From DOM: <button class="listbox-button__control btn btn--form" value="Auction"
                #            aria-haspopup="listbox"> is the trigger
                # Options: <div class="listbox__option" role="option">Buy It Now</div>
                try:
                    format_btn = page.locator('button.listbox-button__control[aria-haspopup="listbox"]').first
                    await format_btn.click(timeout=3000)
                    logger.info("Clicked listbox format button")
                    await page.wait_for_timeout(800)
                    await page.screenshot(path="/tmp/ebay_debug_format_open.png")

                    # Click the "Buy It Now" option in the opened listbox
                    bin_option = page.locator('.listbox__option:has-text("Buy It Now")').first
                    await bin_option.click(timeout=3000)
                    format_changed = True
                    logger.info("Selected 'Buy It Now' from listbox dropdown")
                except (PlaywrightTimeout, Exception) as e:
                    logger.info(f"Listbox button strategy failed: {e}")

                # Strategy 2: Use role selectors as fallback
                if not format_changed:
                    try:
                        # Click button with value="Auction" that has aria-haspopup
                        await page.locator('button[value="Auction"][aria-haspopup]').first.click(timeout=3000)
                        await page.wait_for_timeout(800)
                        await page.locator('[role="option"]:has-text("Buy It Now")').first.click(timeout=3000)
                        format_changed = True
                        logger.info("Selected 'Buy It Now' via role selectors")
                    except (PlaywrightTimeout, Exception) as e:
                        logger.info(f"Role selector strategy failed: {e}")

                # Strategy 3: Click by JS using exact class names from DOM dump
                if not format_changed:
                    try:
                        opened = await page.evaluate("""() => {
                            const btn = document.querySelector('button.listbox-button__control');
                            if (btn) { btn.click(); return true; }
                            return false;
                        }""")
                        if opened:
                            await page.wait_for_timeout(800)
                            selected = await page.evaluate("""() => {
                                const options = document.querySelectorAll('.listbox__option');
                                for (const opt of options) {
                                    if (opt.textContent.includes('Buy It Now')) {
                                        opt.click();
                                        return true;
                                    }
                                }
                                return false;
                            }""")
                            if selected:
                                format_changed = True
                                logger.info("Selected 'Buy It Now' via JS click on listbox elements")
                    except Exception as e:
                        logger.info(f"JS listbox click failed: {e}")

                # Wait for UI to re-render
                await page.wait_for_timeout(3000)

                fmt_val = await page.evaluate("() => document.querySelector('select[name=\"format\"]')?.value || 'N/A'")
                logger.info(f"Format value after change: {fmt_val} (changed={format_changed})")
            except Exception as e:
                logger.warning(f"Format change failed: {e}")

            await page.screenshot(path="/tmp/ebay_debug7b.png")

            # --- Dump all form elements for debugging ---
            form_debug = await page.evaluate("""() => {
                const result = {inputs: [], selects: [], textareas: [], editables: []};
                // Inputs
                for (const inp of document.querySelectorAll('input')) {
                    if (inp.offsetHeight === 0) continue;
                    if (['hidden','file'].includes(inp.type)) continue;
                    result.inputs.push({name: inp.name, type: inp.type, value: inp.value});
                }
                // Selects
                for (const sel of document.querySelectorAll('select')) {
                    result.selects.push({
                        name: sel.name,
                        value: sel.value,
                        options: Array.from(sel.options).map(o => ({value: o.value, text: o.text}))
                    });
                }
                // Textareas
                for (const ta of document.querySelectorAll('textarea')) {
                    result.textareas.push({name: ta.name, value: ta.value.substring(0, 50)});
                }
                // Contenteditable
                for (const div of document.querySelectorAll('div[contenteditable="true"], div[role="textbox"]')) {
                    if (div.offsetHeight > 30)
                        result.editables.push({tag: div.tagName, text: div.innerText.substring(0, 50), h: div.offsetHeight, w: div.offsetWidth});
                }
                return result;
            }""")
            logger.info(f"Form debug: {form_debug}")

            # --- Set price ---
            price_str = f"{price:.2f}"
            fmt_val = await page.evaluate("() => document.querySelector('select[name=\"format\"]')?.value || 'N/A'")

            if fmt_val == "Auction" or fmt_val == "N/A":
                # Format change failed — we're in Auction mode.
                # Fill Starting bid with our price AND fill Buy It Now (optional) field.
                # BIN must be >= 130% of starting bid, so use price as BIN and lower starting bid.
                starting_bid = f"{price * 0.5:.2f}"  # 50% of price as starting bid
                bin_price = price_str  # Full price as BIN
                logger.info(f"In Auction mode: setting starting bid={starting_bid}, BIN={bin_price}")

                try:
                    # Fill starting bid
                    start_input = page.locator('input[name="startPrice"]')
                    await start_input.scroll_into_view_if_needed()
                    await start_input.click(click_count=3, timeout=5000)
                    await page.keyboard.type(starting_bid, delay=30)
                    await page.keyboard.press("Tab")
                    await page.wait_for_timeout(500)

                    # Fill Buy It Now (optional) field
                    bin_input = page.locator('input[name="binPrice"]')
                    await bin_input.click(click_count=3, timeout=5000)
                    await page.keyboard.type(bin_price, delay=30)
                    await page.keyboard.press("Tab")
                    logger.info(f"Set starting bid: {starting_bid}, BIN: {bin_price}")
                except (PlaywrightTimeout, Exception) as e:
                    logger.warning(f"Auction price fill failed: {e}")
            else:
                # Format is Buy It Now — fill the BIN price field
                try:
                    await page.evaluate("""() => {
                        const el = document.querySelector('input[name="binPrice"]')
                            || document.querySelector('input[name="price"]')
                            || document.querySelector('input[name="startPrice"]');
                        if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
                    }""")
                    await page.wait_for_timeout(500)
                    price_input = page.locator(
                        'input[name="binPrice"], input[name="price"], input[name="startPrice"]'
                    ).first
                    await price_input.click(click_count=3, timeout=5000)
                    await page.keyboard.type(price_str, delay=30)
                    await page.keyboard.press("Tab")
                    logger.info(f"Set BIN price: {price_str}")
                except (PlaywrightTimeout, Exception) as e:
                    logger.warning(f"Price fill failed: {e}")

            await page.wait_for_timeout(1000)
            await page.screenshot(path="/tmp/ebay_debug8.png")

            # --- Fill description ---
            # eBay uses a custom rich-text editor. The hidden textarea[name="description"]
            # exists but setting it via JS doesn't work. We must type into the visible editor.
            try:
                # Scroll to description section
                await page.evaluate("""() => {
                    const heading = Array.from(document.querySelectorAll('h3, h2, label, span'))
                        .find(el => /^DESCRIPTION$/i.test(el.textContent.trim()));
                    if (heading) heading.scrollIntoView({behavior: 'instant', block: 'center'});
                }""")
                await page.wait_for_timeout(1000)

                # Debug: log all potentially editable elements (no height filter)
                desc_debug = await page.evaluate("""() => {
                    const result = {iframes: [], editables: [], textareas: [], divs_near_desc: []};
                    for (const f of document.querySelectorAll('iframe')) {
                        result.iframes.push({src: f.src, id: f.id, name: f.name, h: f.offsetHeight, w: f.offsetWidth});
                    }
                    for (const d of document.querySelectorAll('[contenteditable], [role="textbox"]')) {
                        result.editables.push({
                            tag: d.tagName, cls: (d.className || '').substring(0, 100),
                            ce: d.contentEditable, role: d.getAttribute('role'),
                            h: d.offsetHeight, w: d.offsetWidth,
                            text: (d.innerText || '').substring(0, 30)
                        });
                    }
                    for (const t of document.querySelectorAll('textarea')) {
                        result.textareas.push({name: t.name, h: t.offsetHeight, w: t.offsetWidth, hidden: t.hidden || t.offsetHeight === 0});
                    }
                    return result;
                }""")
                logger.info(f"Description debug: {desc_debug}")

                desc_typed = False

                # Strategy 1: Check for description iframe
                if not desc_typed:
                    try:
                        frames = page.frames
                        for frame in frames:
                            if frame == page.main_frame:
                                continue
                            try:
                                body = frame.locator('body')
                                if await body.is_visible(timeout=1000):
                                    await body.click()
                                    await page.wait_for_timeout(300)
                                    await page.keyboard.insert_text(description)
                                    desc_typed = True
                                    logger.info("Typed description via iframe body")
                                    break
                            except Exception:
                                continue
                    except Exception as e:
                        logger.info(f"iframe strategy failed: {e}")

                # Strategy 2: Any contenteditable (no height filter)
                if not desc_typed:
                    for sel in [
                        'div[contenteditable="true"]',
                        '[contenteditable="true"]',
                        'div[role="textbox"]',
                        'div.ql-editor',
                        'div[data-placeholder]',
                    ]:
                        try:
                            el = page.locator(sel).first
                            if await el.is_visible(timeout=1500):
                                await el.click()
                                await page.wait_for_timeout(300)
                                await page.keyboard.insert_text(description)
                                desc_typed = True
                                logger.info(f"Typed description via selector '{sel}'")
                                break
                        except (PlaywrightTimeout, Exception):
                            continue

                # Strategy 3: Click the white editor area relative to "Use AI description"
                # In the screenshot, the editor is the white box ABOVE this button
                if not desc_typed:
                    try:
                        ai_btn = page.get_by_text("Use AI description", exact=False).first
                        bbox = await ai_btn.bounding_box()
                        if bbox:
                            # Click in the center of the white area above the button
                            await page.mouse.click(bbox["x"], bbox["y"] - 80)
                            await page.wait_for_timeout(500)

                            # After clicking, check if a contenteditable appeared
                            ce_appeared = await page.evaluate("""() => {
                                const el = document.activeElement;
                                return {
                                    tag: el?.tagName, ce: el?.contentEditable,
                                    role: el?.getAttribute('role'),
                                    cls: (el?.className || '').substring(0, 80)
                                };
                            }""")
                            logger.info(f"Active element after click: {ce_appeared}")

                            await page.keyboard.insert_text(description)
                            await page.wait_for_timeout(500)

                            # Check if description textarea got the text
                            desc_val = await page.evaluate("() => document.querySelector('textarea[name=\"description\"]')?.value || ''")
                            if desc_val:
                                desc_typed = True
                                logger.info("Description filled via editor click + insertText")
                            else:
                                logger.info("insertText didn't fill textarea, trying type()")
                                # Try regular type as fallback
                                await page.mouse.click(bbox["x"], bbox["y"] - 80)
                                await page.wait_for_timeout(300)
                                await page.keyboard.type(description, delay=8)
                                desc_val = await page.evaluate("() => document.querySelector('textarea[name=\"description\"]')?.value || ''")
                                if desc_val:
                                    desc_typed = True
                                    logger.info("Description filled via editor click + type()")
                    except (PlaywrightTimeout, Exception) as e:
                        logger.info(f"AI button strategy failed: {e}")

                # Strategy 4: Click "Use AI description" to auto-generate (fallback)
                if not desc_typed:
                    try:
                        ai_btn = page.get_by_text("Use AI description", exact=False).first
                        await ai_btn.click(timeout=3000)
                        logger.info("Clicked 'Use AI description' button as fallback")
                        await page.wait_for_timeout(5000)
                        # Check if description got filled
                        desc_val = await page.evaluate("() => document.querySelector('textarea[name=\"description\"]')?.value || ''")
                        if desc_val:
                            desc_typed = True
                            logger.info("Description auto-generated by eBay AI")
                    except (PlaywrightTimeout, Exception) as e:
                        logger.info(f"AI description button failed: {e}")

                # Strategy 5: Direct JS textarea fill (last resort)
                if not desc_typed:
                    logger.warning("Could not type description via UI, trying direct JS fill")
                    await page.evaluate("""(desc) => {
                        const ta = document.querySelector('textarea[name="description"]');
                        if (ta) {
                            const setter = Object.getOwnPropertyDescriptor(
                                HTMLTextAreaElement.prototype, 'value'
                            ).set;
                            setter.call(ta, desc);
                            ta.dispatchEvent(new Event('input', {bubbles: true}));
                            ta.dispatchEvent(new Event('change', {bubbles: true}));
                        }
                    }""", description)
            except Exception as e:
                logger.warning(f"Description fill failed: {e}")

            await page.screenshot(path="/tmp/ebay_debug8b.png")

            # --- Fill item specifics by checking all suggested checkboxes ---
            try:
                # Check all the "extracted-attribute-selector" checkboxes to accept suggestions
                checked_count = await page.evaluate("""() => {
                    let count = 0;
                    const checkboxes = document.querySelectorAll('input[name="extracted-attribute-selector"]');
                    for (const cb of checkboxes) {
                        if (!cb.checked) {
                            cb.click();
                            count++;
                        }
                    }
                    return count;
                }""")
                if checked_count > 0:
                    logger.info(f"Checked {checked_count} item specifics checkboxes")
                    await page.wait_for_timeout(1000)

                    # Click "Apply" or "Add" button for suggested specifics
                    try:
                        apply_btn = page.locator(
                            'button:has-text("Apply"), button:has-text("Add all"), '
                            'button:has-text("Add selected")'
                        ).first
                        await apply_btn.click(timeout=3000)
                        await page.wait_for_timeout(1000)
                        logger.info("Applied item specifics")
                    except (PlaywrightTimeout, Exception):
                        pass
            except Exception as e:
                logger.warning(f"Item specifics fill failed: {e}")

            # --- Set shipping by clicking the visible dropdown ---
            try:
                await page.evaluate("""() => {
                    const el = document.querySelector('select[name="domesticShippingType"]');
                    if (el) el.scrollIntoView({behavior: 'instant', block: 'center'});
                }""")
                await page.wait_for_timeout(500)

                # Click the visible shipping dropdown (shows "Standard shipping: Small to medium items")
                ship_changed = False
                try:
                    ship_dropdown = page.get_by_text("Standard shipping", exact=False).first
                    await ship_dropdown.click(timeout=3000)
                    await page.wait_for_timeout(500)

                    # Click "Local pickup only" or "No shipping" option
                    for opt_text in ["Local pickup only", "Local pickup", "No shipping", "Pickup"]:
                        try:
                            await page.get_by_text(opt_text, exact=False).first.click(timeout=2000)
                            ship_changed = True
                            logger.info(f"Selected shipping: {opt_text}")
                            break
                        except (PlaywrightTimeout, Exception):
                            continue
                except (PlaywrightTimeout, Exception):
                    pass

                if not ship_changed:
                    # Try clicking "See shipping options"
                    try:
                        await page.get_by_text("See shipping options", exact=False).first.click(timeout=3000)
                        await page.wait_for_timeout(1000)
                        for opt_text in ["Local pickup only", "Local pickup", "No shipping"]:
                            try:
                                await page.get_by_text(opt_text, exact=False).first.click(timeout=2000)
                                ship_changed = True
                                logger.info(f"Selected shipping via options: {opt_text}")
                                break
                            except (PlaywrightTimeout, Exception):
                                continue
                    except (PlaywrightTimeout, Exception):
                        pass

                ship_val = await page.evaluate("() => document.querySelector('select[name=\"domesticShippingType\"]')?.value || 'N/A'")
                logger.info(f"Shipping value: {ship_val}")
                await page.wait_for_timeout(1000)
            except Exception as e:
                logger.warning(f"Shipping change failed: {e}")

            # --- Step 6: Submit listing ---
            # Scroll back to top to check for any remaining required fields
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(1000)

            # Scroll to the List it button at bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

            try:
                submit_btn = page.locator(
                    'button:has-text("List it"), button:has-text("List item"), '
                    'button:has-text("Submit"), button:has-text("Publish")'
                ).first
                await submit_btn.scroll_into_view_if_needed()
                await submit_btn.click(timeout=8000)
                logger.info("Clicked submit button")
                await page.wait_for_timeout(8000)
            except PlaywrightTimeout:
                logger.info("No submit button found, listing may be saved as draft")

            final_url = page.url
            await page.screenshot(path="/tmp/ebay_debug_final.png")
            logger.info(f"Final URL: {final_url}")

            # Check for success — must NOT still be on the listing editor or login page
            page_text = await page.text_content("body") or ""
            still_on_editor = (
                "/lstng" in final_url
                or "sl/list" in final_url
                or "sl/prelist" in final_url
            )
            hit_login = "signin.ebay" in final_url or "sign in to your account" in page_text.lower()
            has_validation_error = "looks like something is missing" in page_text.lower()

            # Log specific validation errors if present
            if has_validation_error:
                # Extract the error links (Description, Photos, Buy It Now price, etc.)
                error_links = await page.locator(
                    'a[href*="#"], span:near(:text("missing"))'
                ).all_text_contents()
                logger.warning(f"eBay validation errors: {error_links}")

            success = (
                "ebay.com" in final_url
                and not still_on_editor
                and not hit_login
                and not has_validation_error
                and (
                    "success" in page_text.lower()
                    or "congratulations" in page_text.lower()
                    or "your listing is live" in page_text.lower()
                )
            )

            await page.context.browser.close()
            pw = None

            if hit_login:
                error_msg = "eBay session expired — redirected to login page. Re-authenticate Browserbase."
            elif has_validation_error:
                error_msg = f"eBay validation errors on listing form. Final URL: {final_url}"
            elif not success:
                error_msg = f"eBay posting may have failed. Final URL: {final_url}"
            else:
                error_msg = None

            return PostingResult(
                success=success,
                external_url=final_url if success else None,
                error_message=error_msg,
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
