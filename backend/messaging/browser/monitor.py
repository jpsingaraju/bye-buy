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
from .client import get_stagehand_session, close_session
from .extractor import extract_conversation_list, extract_conversation_messages
from .actions import (
    navigate_to_marketplace,
    click_conversation,
    send_message as browser_send_message,
    go_back_to_conversation_list,
)
from ..ai.responder import generate_response

logger = logging.getLogger(__name__)


class MessageMonitor:
    """Main polling loop for monitoring Messenger conversations."""

    def __init__(self):
        self.running = False
        self.cycle_count = 0
        self.last_poll_at: datetime | None = None
        self.recent_errors: deque[str] = deque(maxlen=20)
        self._task: asyncio.Task | None = None

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
        """Main loop with randomized intervals and session breaks."""
        while self.running:
            try:
                await self._poll_cycle()
                self.cycle_count += 1
                self.last_poll_at = datetime.utcnow()

                # Session break every N cycles
                if self.cycle_count % settings.session_break_cycles == 0:
                    break_time = random.uniform(
                        settings.session_break_min, settings.session_break_max
                    )
                    logger.info(f"Session break: sleeping {break_time:.0f}s")
                    await asyncio.sleep(break_time)
                else:
                    # Randomized poll interval
                    interval = random.uniform(
                        settings.poll_interval_min, settings.poll_interval_max
                    )
                    await asyncio.sleep(interval)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                error_msg = f"Poll cycle error: {e}"
                logger.error(error_msg)
                self.recent_errors.append(error_msg)
                await asyncio.sleep(settings.poll_interval_max)

    async def _poll_cycle(self):
        """Single poll cycle: check conversations and respond."""
        session = await get_stagehand_session()

        # Navigate to marketplace
        if not await navigate_to_marketplace(session):
            return

        # Extract conversation list
        conversations = await extract_conversation_list(session)
        if not conversations:
            return

        # Determine which conversations to check (hybrid detection)
        is_full_sweep = (self.cycle_count % settings.full_sweep_interval == 0)
        if is_full_sweep:
            targets = conversations
            logger.info(f"Full sweep: checking all {len(targets)} conversations")
        else:
            targets = [c for c in conversations if c.is_unread]
            if not targets:
                return

        # Limit conversations per cycle
        targets = targets[: settings.max_conversations_per_cycle]

        for conv_preview in targets:
            try:
                await self._handle_conversation(session, conv_preview)
            except Exception as e:
                error_msg = f"Error handling {conv_preview.buyer_name}: {e}"
                logger.error(error_msg)
                self.recent_errors.append(error_msg)

        # Go back to list view after processing
        await go_back_to_conversation_list(session)

    async def _handle_conversation(self, browser_session, conv_preview):
        """Handle a single conversation: extract, diff, respond, save."""
        buyer_name = conv_preview.buyer_name

        # Click into conversation
        if not await click_conversation(browser_session, buyer_name):
            return

        # Extract messages
        conv_data = await extract_conversation_messages(browser_session)
        if not conv_data.messages:
            await go_back_to_conversation_list(browser_session)
            return

        async with async_session() as db:
            # Get or create buyer
            buyer = await BuyerService.get_or_create(db, fb_name=buyer_name)

            # Match listing
            listing = await MatchingService.match_listing(
                db, conv_data.listing_title
            )
            listing_id = listing.id if listing else None

            # Get or create conversation
            conversation = await ConversationService.get_or_create(
                db, buyer_id=buyer.id, listing_id=listing_id
            )

            # Skip if conversation is closed/sold
            if conversation.status in ("closed", "sold"):
                await go_back_to_conversation_list(browser_session)
                return

            # DB diff: find truly new messages
            existing_messages = await ConversationService.get_messages(
                db, conversation.id, limit=200
            )
            existing_contents = {m.content for m in existing_messages}

            new_buyer_messages = []
            for msg in conv_data.messages:
                if msg.is_from_buyer and msg.content not in existing_contents:
                    new_buyer_messages.append(msg)

            if not new_buyer_messages:
                await go_back_to_conversation_list(browser_session)
                return

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
                    "Hey, sorry but this item has already been sold! Thanks for "
                    "your interest though."
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
                await go_back_to_conversation_list(browser_session)
                return

            # Generate AI response
            all_messages = await ConversationService.get_messages(
                db, conversation.id, limit=50
            )
            ai_result = await generate_response(
                listing=listing,
                messages=all_messages,
            )

            if not ai_result:
                await go_back_to_conversation_list(browser_session)
                return

            # Send AI response
            sent = await browser_send_message(browser_session, ai_result.message)

            # Save seller message
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
                print(
                    f"DEAL REACHED: {listing.title if listing else 'Unknown'} - "
                    f"Buyer: {buyer_name} - ${agreed_price}"
                )
                await ConversationService.update_status(
                    db, conversation.id, "sold"
                )
                # Update listing status
                if listing:
                    listing.status = "sold"
                    await db.commit()

            elif ai_result.deal_status == "needs_review":
                print(
                    f"NEEDS REVIEW: {listing.title if listing else 'Unknown'} - "
                    f"Buyer: {buyer_name}"
                )
                await ConversationService.update_status(
                    db, conversation.id, "needs_review"
                )

        await go_back_to_conversation_list(browser_session)


# Global monitor instance
monitor = MessageMonitor()
