import asyncio
import logging
import random
from collections import deque
from datetime import datetime

from database.connection import async_session
from database.models.listing import Listing
from ..services.buyer_service import BuyerService
from ..services.conversation_service import ConversationService
from ..services.matching_service import MatchingService
from ..config import settings
from .client import get_stagehand_session, close_session, reset_session
from .extractor import extract_conversation_list, extract_chat_messages
from .actions import (
    navigate_to_marketplace,
    click_conversation,
    send_message as browser_send_message,
    close_chat_popup,
)
from ..ai.responder import generate_response

logger = logging.getLogger(__name__)

# Max consecutive checks with no new messages before closing a chat popup
MAX_IDLE_CHECKS = 3


class MessageMonitor:
    """Main polling loop for monitoring Marketplace conversations."""

    def __init__(self):
        self.running = False
        self.cycle_count = 0
        self.last_poll_at: datetime | None = None
        self.recent_errors: deque[str] = deque(maxlen=20)
        self._task: asyncio.Task | None = None
        self._on_inbox = False

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
        """Main loop with two-phase polling.

        - Navigate to inbox, extract conversations
        - For each conversation: open chat popup, watch it (re-extract
          every 2-5s since FB updates it live), respond when new messages
          appear, close popup after MAX_IDLE_CHECKS with no new messages
        - If a listing gets sold mid-cycle, remaining conversations for
          that listing get a "sorry already sold" message
        - After a sale: notify all remaining buyers, then close session
        - If no conversations found: refresh inbox every 5-10s (idle polling)
        - After handling conversations: refresh inbox every ~30s
        """
        while self.running:
            try:
                deal_completed = await self._poll_cycle()
                self.cycle_count += 1
                self.last_poll_at = datetime.utcnow()

                if deal_completed:
                    # Sale happened — session closed by _poll_cycle, reset state
                    self._on_inbox = False
                    logger.info("Deal completed, waiting before starting new session")
                    await asyncio.sleep(5)
                    continue

                # Session break every N cycles
                if self.cycle_count % settings.session_break_cycles == 0:
                    self._on_inbox = False
                    break_time = random.uniform(
                        settings.session_break_min, settings.session_break_max
                    )
                    logger.info(f"Session break: sleeping {break_time:.0f}s")
                    await asyncio.sleep(break_time)
                else:
                    # Refresh inbox after ~30s to check for new conversations
                    interval = random.uniform(25, 35)
                    logger.info(f"Next inbox refresh in {interval:.0f}s")
                    self._on_inbox = False
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

    async def _poll_cycle(self) -> bool:
        """Single poll cycle. Returns True if a deal was completed (session closed)."""
        session = await get_stagehand_session()

        # Navigate to marketplace inbox
        if not self._on_inbox:
            if not await navigate_to_marketplace(session):
                return False
            self._on_inbox = True

        # Extract conversation list
        conversations = await extract_conversation_list(session)
        if not conversations:
            logger.info("No conversations found, will retry soon")
            # Idle polling — refresh quickly
            self._on_inbox = False
            await asyncio.sleep(random.uniform(5, 10))
            return False

        targets = conversations[: settings.max_conversations_per_cycle]
        logger.info(f"Checking {len(targets)} conversations")

        handled_listings = set()
        deal_completed = False

        for conv_preview in targets:
            try:
                result = await self._handle_conversation(
                    session, conv_preview, handled_listings
                )
                if result == "sold":
                    deal_completed = True
            except Exception as e:
                error_msg = f"Error handling {conv_preview.buyer_name}: {e}"
                logger.error(error_msg)
                self.recent_errors.append(error_msg)

        if deal_completed:
            # All conversations processed (remaining ones got "already sold")
            # Now close the session
            logger.info("All buyers notified, closing Browserbase session")
            await close_session()
            self._on_inbox = False

        return deal_completed

    async def _handle_conversation(
        self, browser_session, conv_preview, handled_listings: set
    ) -> str | None:
        """Handle a single conversation with live chat watching.

        Returns "sold" if the listing was sold, None otherwise.
        """
        buyer_name = conv_preview.buyer_name

        # Click conversation to open chat popup
        if not await click_conversation(browser_session, buyer_name):
            return None

        # Watch the chat popup — re-extract every 2-5s, respond when
        # new messages appear, bail after MAX_IDLE_CHECKS with nothing new
        idle_checks = 0
        result = None

        while idle_checks < MAX_IDLE_CHECKS:
            conv_data = await extract_chat_messages(browser_session)

            # Deduplicate by listing title
            dedup_key = conv_data.listing_title.lower().strip()
            if dedup_key and dedup_key in handled_listings:
                logger.info(
                    f"Already handled '{conv_data.listing_title}' this cycle, "
                    f"skipping {buyer_name}"
                )
                await close_chat_popup(browser_session)
                return None
            if dedup_key:
                handled_listings.add(dedup_key)

            logger.info(
                f"Chat popup for {buyer_name}: {len(conv_data.messages)} messages, "
                f"listing='{conv_data.listing_title}'"
            )

            if not conv_data.messages:
                idle_checks += 1
                await asyncio.sleep(random.uniform(2, 5))
                continue

            # Skip if last message is from seller — waiting for buyer reply
            if not conv_data.messages[-1].is_from_buyer:
                logger.info(f"Last message for {buyer_name} is from seller, waiting...")
                idle_checks += 1
                await asyncio.sleep(random.uniform(2, 5))
                continue

            # Process messages against DB
            action = await self._process_messages(
                browser_session, buyer_name, conv_data
            )

            if action == "sold":
                result = "sold"
                break
            elif action == "responded":
                # We responded — keep watching for buyer's next message
                idle_checks = 0
                await asyncio.sleep(random.uniform(2, 5))
                continue
            else:
                # No new messages (all already in DB)
                idle_checks += 1
                await asyncio.sleep(random.uniform(2, 5))
                continue

        if result != "sold":
            await close_chat_popup(browser_session)

        return result

    async def _process_messages(
        self, browser_session, buyer_name: str, conv_data
    ) -> str | None:
        """Process extracted messages: diff against DB, generate AI response.

        Returns:
            "sold" — listing was sold (address received)
            "responded" — we sent a response to new messages
            None — no new messages to respond to
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

            # Skip if conversation is closed/sold
            if conversation.status in ("closed", "sold"):
                return None

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

            # Check if listing is sold — tell buyer
            if listing and listing.status == "sold":
                response_text = (
                    "ay sorry someone already grabbed this one, "
                    "appreciate you reaching out tho. bye buy!"
                )
                sent = await browser_send_message(browser_session, response_text)
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
                await close_chat_popup(browser_session)
                return None

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
            )

            if not ai_result:
                logger.warning(f"No AI response generated for {buyer_name}")
                return None

            logger.info(
                f"AI response for {buyer_name}: {ai_result.message[:100]} "
                f"(deal_status={ai_result.deal_status})"
            )

            # Send AI response
            sent = await browser_send_message(browser_session, ai_result.message)
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
                    db, conversation.id, "pending_address"
                )

            elif ai_result.deal_status == "address_received":
                delivery_address = ai_result.delivery_address
                if delivery_address:
                    logger.info(
                        f"ADDRESS RECEIVED: "
                        f"{listing.title if listing else 'Unknown'} - "
                        f"Buyer: {buyer_name} - Address: {delivery_address}"
                    )
                    await ConversationService.save_deal_details(
                        db, conversation.id, delivery_address=delivery_address
                    )
                    await ConversationService.update_status(
                        db, conversation.id, "sold"
                    )
                    if listing:
                        listing.status = "sold"
                        await db.commit()

                    await close_chat_popup(browser_session)
                    return "sold"
                else:
                    logger.warning(
                        f"address_received but no address extracted for {buyer_name}"
                    )

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


# Global monitor instance
monitor = MessageMonitor()
