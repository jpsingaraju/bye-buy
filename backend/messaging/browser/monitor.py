import asyncio
import logging
import random
from collections import deque
from datetime import datetime

from sqlalchemy import select

from database.connection import async_session
from ..models.transaction import Transaction
from ..services.buyer_service import BuyerService
from ..services.conversation_service import ConversationService
from ..services.matching_service import MatchingService
from ..config import settings
from .client import get_stagehand_session, close_session, reset_session
from .extractor import extract_conversation_list, extract_chat_messages
from .actions import (
    navigate_to_marketplace,
    refresh_inbox,
    click_conversation,
    close_all_popups,
    send_message as browser_send_message,
)
from ..ai.responder import generate_response

logger = logging.getLogger(__name__)

# Refresh interval when idle (no unread messages)
IDLE_REFRESH_MIN = 9
IDLE_REFRESH_MAX = 11

# Refresh interval when active (just responded)
ACTIVE_REFRESH_MIN = 3
ACTIVE_REFRESH_MAX = 5


class MessageMonitor:
    """Main polling loop for monitoring Marketplace conversations."""

    def __init__(self):
        self.running = False
        self.cycle_count = 0
        self.last_poll_at: datetime | None = None
        self.recent_errors: deque[str] = deque(maxlen=20)
        self._task: asyncio.Task | None = None
        self._on_inbox = False
        self._consecutive_idle = 0  # refresh page after 3 idle cycles
        # Track last seen inbox preview per buyer to detect new activity
        # Compare current preview to stored: same → skip, different → open & check
        self._last_seen_preview: dict[str, str] = {}
        # Buyers with confirmed deals awaiting payment — always re-check these
        self._awaiting_payment: set[str] = set()

    async def start(self):
        """Start the monitoring loop."""
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Message monitor started")

    async def stop(self):
        """Stop the monitoring loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await close_session()
        logger.info("Message monitor stopped")

    async def _run(self):
        """Main loop: single-pass per conversation, fast refresh on activity.

        - Navigate to inbox, extract conversations
        - For each conversation: open popup, check once, respond if needed, close
        - If any response sent: force refresh inbox, wait 2-5s
        - If idle (no new messages): wait 5-10s
        - If empty (no conversations): wait 5-10s
        """
        while self.running:
            try:
                result = await self._poll_cycle()
                self.cycle_count += 1
                self.last_poll_at = datetime.utcnow()

                if result == "deal_completed":
                    self._on_inbox = False
                    logger.info("Deal completed, shutting down service")
                    self.running = False
                    import os
                    import signal
                    os.kill(os.getpid(), signal.SIGINT)
                    return

                # Session break every N cycles
                if self.cycle_count % settings.session_break_cycles == 0:
                    self._on_inbox = False
                    break_time = random.uniform(
                        settings.session_break_min, settings.session_break_max
                    )
                    logger.info(f"Session break: sleeping {break_time:.0f}s")
                    await asyncio.sleep(break_time)
                elif result == "responded":
                    interval = random.uniform(ACTIVE_REFRESH_MIN, ACTIVE_REFRESH_MAX)
                    await asyncio.sleep(interval)
                else:
                    # Idle — wait longer before refreshing
                    interval = random.uniform(IDLE_REFRESH_MIN, IDLE_REFRESH_MAX)
                    await asyncio.sleep(interval)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                error_msg = f"Poll cycle error: {e}"
                logger.error(error_msg)
                self.recent_errors.append(error_msg)
                self._on_inbox = False

                if "410" in str(e) or "Gone" in str(e):
                    logger.warning("Session expired (410 Gone), resetting...")
                    await reset_session()

                await asyncio.sleep(10)

    async def _poll_cycle(self) -> str:
        """Single poll cycle: extract inbox, process unread conversations bottom-to-top.

        Only opens conversations marked as unread (new buyer activity).
        Processes bottom-to-top so the most neglected conversations get attention first.
        If nothing is unread, returns "idle" and the caller sleeps before re-extracting.

        Returns:
            "deal_completed" - item sold, session closed
            "empty" - no conversations found
            "responded" - at least one conversation got a response
            "idle" - conversations exist but none are unread
        """
        session = await get_stagehand_session()

        # Navigate to marketplace inbox
        if not self._on_inbox:
            if not await navigate_to_marketplace(session):
                return "empty"
            self._on_inbox = True

        # Extract conversation list
        conversations = await extract_conversation_list(session)
        if not conversations:
            logger.info("No conversations found, will retry soon")
            self._on_inbox = False
            return "empty"

        # Filter using preview comparison: if preview hasn't changed since
        # last time we processed this buyer, skip without opening
        # Exception: always re-check buyers awaiting payment
        unread = []
        for c in conversations:
            if c.buyer_name in self._awaiting_payment:
                unread.append(c)
                continue
            last_preview = self._last_seen_preview.get(c.buyer_name)
            if last_preview and c.preview_text == last_preview:
                logger.info(f"Skipping {c.buyer_name} (preview unchanged)")
                continue
            if c.is_unread:
                unread.append(c)

        # Process bottom-to-top (most neglected first)
        unread.reverse()

        logger.info(
            f"Inbox: {len(conversations)} total, {len(unread)} unread "
            f"(processing bottom-to-top)"
        )

        if not unread:
            self._consecutive_idle += 1
            if self._consecutive_idle >= 3:
                logger.info("3 idle cycles, refreshing page")
                self._consecutive_idle = 0
                self._on_inbox = False
            return "idle"

        self._consecutive_idle = 0
        any_responded = False

        # Collect all buyer names so we can filter cross-talk from sidebar
        all_buyer_names = {c.buyer_name for c in conversations}

        for conv_preview in unread:
            try:
                result = await self._handle_conversation(
                    session, conv_preview, all_buyer_names
                )
                # Only cache preview if we actually processed the conversation.
                # If result is None due to buyer mismatch (wrong chat opened),
                # don't cache — so we retry next cycle.
                if result is not None:
                    self._last_seen_preview[conv_preview.buyer_name] = conv_preview.preview_text
                if result == "sold":
                    self._awaiting_payment.discard(conv_preview.buyer_name)
                    logger.info("Item sold, closing Browserbase session")
                    await close_session()
                    self._on_inbox = False
                    return "deal_completed"
                elif result == "responded":
                    any_responded = True
            except Exception as e:
                error_msg = f"Error handling {conv_preview.buyer_name}: {e}"
                logger.error(error_msg)
                self.recent_errors.append(error_msg)

        return "responded" if any_responded else "idle"

    async def _handle_conversation(
        self, browser_session, conv_preview, all_buyer_names: set[str] | None = None
    ) -> str | None:
        """Handle a single conversation.

        Clicks the conversation row in the inbox list to show messages
        in the conversation panel, extracts messages, and responds if needed.

        Returns: "sold", "responded", or None
        """
        display_name = conv_preview.display_name or conv_preview.buyer_name
        buyer_name = conv_preview.buyer_name  # normalized for DB

        logger.info(
            f"[handle_conversation] START: preview_buyer='{buyer_name}', "
            f"display_name='{display_name}', preview_listing='{conv_preview.listing_title}', "
            f"preview_text='{conv_preview.preview_text[:60]}', unread={conv_preview.is_unread}"
        )

        # Close any auto-opened chat popups before clicking so we don't
        # accidentally extract/send in the wrong panel
        await close_all_popups(browser_session)

        # Click conversation row to show messages in panel
        if not await click_conversation(browser_session, display_name):
            logger.warning(f"[handle_conversation] Failed to click conversation for '{display_name}'")
            return None

        try:
            # Pass other buyer names so extractor can filter sidebar cross-talk
            other_buyers = list(all_buyer_names - {buyer_name}) if all_buyer_names else None
            conv_data = await extract_chat_messages(
                browser_session, buyer_name=display_name, other_buyers=other_buyers
            )

            # Validate extracted buyer matches expected — prevents cross-talk
            logger.info(
                f"[handle_conversation] COMPARE: preview_buyer='{buyer_name}' vs "
                f"extracted_buyer='{conv_data.buyer_name}' (display='{conv_data.display_name}')"
            )
            extracted = conv_data.buyer_name
            # Inbox often shows first name only ("anita") while chat shows
            # full name ("anita moorthy") — accept if one starts with the other
            names_match = (
                not extracted
                or extracted == buyer_name
                or extracted.startswith(buyer_name)
                or buyer_name.startswith(extracted)
            )
            if not names_match:
                logger.warning(
                    f"[handle_conversation] BUYER MISMATCH: expected '{buyer_name}' but extracted "
                    f"'{extracted}' — closing and skipping"
                )
                await close_all_popups(browser_session)
                return None

            logger.info(
                f"[handle_conversation] Conversation {buyer_name}: {len(conv_data.messages)} messages, "
                f"listing='{conv_data.listing_title}'"
            )

            if not conv_data.messages:
                await close_all_popups(browser_session)
                return None

            # Check payment status for confirmed deals
            payment_result = await self._check_payment_status(
                browser_session, buyer_name, conv_data
            )
            if payment_result == "sold":
                return "sold"

            # Last message is from seller — nothing to do
            if not conv_data.messages[-1].is_from_buyer:
                logger.info(f"Last message for {buyer_name} is from seller, skipping")
                await close_all_popups(browser_session)
                return None

            # Process messages against DB
            result = await self._process_messages(
                browser_session, buyer_name, conv_data
            )

            # Always close popups after handling, then refresh if we responded
            await close_all_popups(browser_session)
            if result == "responded" or result == "sold":
                await refresh_inbox(browser_session)

            return result

        except Exception as e:
            logger.error(f"Error handling conversation for {buyer_name}: {e}")
            await close_all_popups(browser_session)
            return None

    async def _process_messages(
        self, browser_session, buyer_name: str, conv_data
    ) -> str | None:
        """Process extracted messages: diff against DB, generate AI response.

        Returns: "sold", "responded", or None
        """
        async with async_session() as db:
            buyer = await BuyerService.get_or_create(db, fb_name=buyer_name)

            listing = await MatchingService.match_listing(
                db, conv_data.listing_title
            )
            listing_id = listing.id if listing else None

            conversation = await ConversationService.get_or_create(
                db, buyer_id=buyer.id, listing_id=listing_id
            )

            # Skip if listing already sold
            if conversation.status == "sold":
                return None

            # Reopen closed/declined conversations if buyer messages again
            if conversation.status == "closed":
                # Check if another buyer already has a pending deal on this listing
                if listing_id and await ConversationService.has_pending_deal(db, listing_id):
                    # Someone else agreed — tell this buyer
                    response_text = (
                        "sorry someone just grabbed this, ill lmk if it falls through. bye buy!"
                    )
                    sent = await browser_send_message(browser_session, response_text, buyer_name=buyer_name)
                    await ConversationService.add_message(
                        db,
                        conversation_id=conversation.id,
                        role="seller",
                        content=response_text,
                        delivered=sent,
                    )
                    return "responded"
                else:
                    await ConversationService.update_status(
                        db, conversation.id, "active"
                    )
                    conversation.status = "active"
                    logger.info(f"Reopened closed conversation for {buyer_name}")

            # Check if payment came through for confirmed deals
            if conversation.status == "confirmed":
                result = await self._check_payment_and_thank(
                    db, browser_session, conversation, listing, buyer_name
                )
                if result:
                    return result

            # DB diff: find truly new messages
            existing_messages = await ConversationService.get_messages(
                db, conversation.id, limit=200
            )
            existing_contents = {m.content for m in existing_messages}

            new_buyer_messages = [
                msg
                for msg in conv_data.messages
                if msg.is_from_buyer and msg.content not in existing_contents
            ]

            if not new_buyer_messages:
                return None

            logger.info(
                f"New messages from {buyer_name}: "
                f"{[m.content[:50] for m in new_buyer_messages]}"
            )

            # Save new buyer messages to DB
            for msg in new_buyer_messages:
                await ConversationService.add_message(
                    db,
                    conversation_id=conversation.id,
                    role="buyer",
                    content=msg.content,
                    delivered=True,
                )

            # Check if listing is sold - tell buyer
            if listing and listing.status == "sold":
                response_text = (
                    "ay sorry someone already grabbed this one, "
                    "appreciate you reaching out tho. bye buy!"
                )
                sent = await browser_send_message(browser_session, response_text, buyer_name=buyer_name)
                await ConversationService.add_message(
                    db,
                    conversation_id=conversation.id,
                    role="seller",
                    content=response_text,
                    delivered=sent,
                )
                await ConversationService.update_status(
                    db, conversation.id, "closed"
                )
                return "responded"

            # Query competing offers from other buyers on the same listing
            competing_offer = None
            if listing_id:
                competing_offer = await ConversationService.get_competing_offer(
                    db, listing_id, conversation.id
                )
                if competing_offer:
                    logger.info(
                        f"Competing offer for {buyer_name}: ${competing_offer:.0f}"
                    )

            # Generate AI response
            all_messages = await ConversationService.get_messages(
                db, conversation.id, limit=50
            )
            new_contents = [m.content for m in new_buyer_messages]
            ai_result = await generate_response(
                listing=listing,
                messages=all_messages,
                conversation_status=conversation.status,
                new_buyer_messages=new_contents,
                agreed_price=conversation.agreed_price,
                competing_offer=competing_offer,
                delivery_address=conversation.delivery_address,
            )

            if not ai_result:
                logger.warning(f"No AI response generated for {buyer_name}")
                return None

            logger.info(
                f"AI response for {buyer_name}: {ai_result.message[:100]} "
                f"(deal_status={ai_result.deal_status})"
            )

            # Send AI response
            sent = await browser_send_message(browser_session, ai_result.message, buyer_name=buyer_name)
            logger.info(
                f"Message send {'succeeded' if sent else 'FAILED'} for {buyer_name}"
            )

            await ConversationService.add_message(
                db,
                conversation_id=conversation.id,
                role="seller",
                content=ai_result.message,
                delivered=sent,
            )

            # Store buyer's offer if extracted
            if ai_result.buyer_offer is not None:
                await ConversationService.update_offer(
                    db, conversation.id, ai_result.buyer_offer
                )
                logger.info(
                    f"Stored buyer offer for {buyer_name}: ${ai_result.buyer_offer:.0f}"
                )

            # Handle deal status
            if ai_result.deal_status == "agreed":
                agreed_price = ai_result.agreed_price or (
                    listing.price if listing else 0
                )
                logger.info(
                    f"DEAL AGREED (awaiting address): "
                    f"{listing.title if listing else 'Unknown'} - "
                    f"Buyer: {buyer_name} - ${agreed_price}"
                )
                await ConversationService.save_deal_details(
                    db, conversation.id, agreed_price=agreed_price
                )
                await ConversationService.update_status(
                    db, conversation.id, "pending"
                )

                # Close competing conversations on this listing
                if listing_id:
                    closed_count = await ConversationService.close_competing_conversations(
                        db, listing_id, conversation.id
                    )
                    if closed_count:
                        logger.info(
                            f"Closed {closed_count} competing conversation(s) "
                            f"on listing '{listing.title}'"
                        )

            elif ai_result.deal_status == "address_received":
                delivery_address = ai_result.delivery_address
                if delivery_address:
                    logger.info(
                        f"ADDRESS RECEIVED (awaiting confirmation): "
                        f"{listing.title if listing else 'Unknown'} - "
                        f"Buyer: {buyer_name} - Address: {delivery_address}"
                    )
                    await ConversationService.save_deal_details(
                        db, conversation.id, delivery_address=delivery_address
                    )
                    await ConversationService.update_status(
                        db, conversation.id, "awaiting_confirm"
                    )
                else:
                    logger.warning(
                        f"address_received but no address extracted for {buyer_name}"
                    )

            elif ai_result.deal_status == "address_confirmed":
                logger.info(
                    f"ADDRESS CONFIRMED: "
                    f"{listing.title if listing else 'Unknown'} - "
                    f"Buyer: {buyer_name}"
                )
                await ConversationService.update_status(
                    db, conversation.id, "confirmed"
                )
                self._awaiting_payment.add(buyer_name)

                # Create checkout session and send payment link in chat
                try:
                    from ..services.payment_service import PaymentService
                    txn = await PaymentService.create_checkout(db, conversation.id)
                    if txn and txn.checkout_url:
                        price_str = f"{conversation.agreed_price:.0f}" if conversation.agreed_price else "the agreed amount"
                        payment_msg = f"here's the payment link for ${price_str}: {txn.checkout_url}"
                        sent = await browser_send_message(browser_session, payment_msg, buyer_name=buyer_name)
                        await ConversationService.add_message(
                            db,
                            conversation_id=conversation.id,
                            role="seller",
                            content=payment_msg,
                            delivered=sent,
                        )
                        logger.info(f"Payment link sent to {buyer_name}: {txn.checkout_url}")
                except Exception as e:
                    logger.error(f"Failed to create checkout for conversation {conversation.id}: {e}")

            elif ai_result.deal_status == "declined":
                logger.info(
                    f"DEAL DECLINED: {listing.title if listing else 'Unknown'} - "
                    f"Buyer: {buyer_name}"
                )
                await ConversationService.update_status(
                    db, conversation.id, "closed"
                )

            elif ai_result.deal_status == "needs_review":
                logger.info(
                    f"NEEDS REVIEW: {listing.title if listing else 'Unknown'} - "
                    f"Buyer: {buyer_name}"
                )
                await ConversationService.update_status(
                    db, conversation.id, "needs_review"
                )

            return "responded"

    async def _check_payment_status(
        self, browser_session, buyer_name: str, conv_data
    ) -> str | None:
        """Check if a confirmed deal has been paid, independent of new messages.

        Returns "sold" if payment went through, None otherwise.
        """
        async with async_session() as db:
            buyer = await BuyerService.get_or_create(db, fb_name=buyer_name)
            listing = await MatchingService.match_listing(db, conv_data.listing_title)
            listing_id = listing.id if listing else None
            conversation = await ConversationService.get_or_create(
                db, buyer_id=buyer.id, listing_id=listing_id
            )
            if conversation.status != "confirmed":
                return None
            return await self._check_payment_and_thank(
                db, browser_session, conversation, listing, buyer_name
            )

    async def _check_payment_and_thank(
        self, db, browser_session, conversation, listing, buyer_name: str
    ) -> str | None:
        """Check if buyer has paid (polling Stripe directly) and send thank-you.

        Returns "sold" if payment confirmed and thank-you sent, None otherwise.
        """
        result = await db.execute(
            select(Transaction).where(
                Transaction.conversation_id == conversation.id
            )
        )
        txn = result.scalar_one_or_none()

        if not txn:
            return None

        # If webhook already updated it, great. Otherwise check Stripe directly.
        if txn.status == "pending" and txn.stripe_checkout_session_id:
            try:
                import stripe
                from ..config import settings
                stripe.api_key = settings.stripe_secret_key
                stripe_session = stripe.checkout.Session.retrieve(txn.stripe_checkout_session_id)
                if stripe_session.payment_status == "paid":
                    from datetime import datetime
                    txn.stripe_payment_intent_id = stripe_session.payment_intent
                    txn.status = "payment_held"
                    txn.paid_at = datetime.utcnow()
                    txn.updated_at = datetime.utcnow()
                    await db.commit()
                    logger.info(f"Payment confirmed via Stripe polling for transaction {txn.id}")
            except Exception as e:
                logger.error(f"Failed to check Stripe session: {e}")

        if txn.status != "payment_held":
            return None

        logger.info(
            f"PAYMENT CONFIRMED: {listing.title if listing else 'Unknown'} - "
            f"Buyer: {buyer_name}"
        )

        # Update conversation to accepted
        await ConversationService.update_status(db, conversation.id, "accepted")

        # Mark listing as sold
        if listing:
            listing.status = "sold"
            await db.commit()

        # Send thank-you message
        thank_msg = "payment received, appreciate it! bye buy!"
        sent = await browser_send_message(browser_session, thank_msg, buyer_name=buyer_name)
        await ConversationService.add_message(
            db,
            conversation_id=conversation.id,
            role="seller",
            content=thank_msg,
            delivered=sent,
        )

        logger.info(f"Thank-you message sent to {buyer_name}")
        return "sold"


# Global monitor instance
monitor = MessageMonitor()
