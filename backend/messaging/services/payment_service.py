import logging
from datetime import datetime

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.transaction import Transaction
from ..models.conversation import Conversation

logger = logging.getLogger(__name__)

stripe.api_key = settings.stripe_secret_key


class PaymentService:
    @staticmethod
    async def create_checkout(session: AsyncSession, conversation_id: int) -> Transaction | None:
        """Create a Stripe Checkout Session and save the transaction."""
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation or not conversation.agreed_price:
            logger.error(f"Conversation {conversation_id} not found or no agreed price")
            return None

        amount_cents = int(conversation.agreed_price * 100)

        # Check for existing transaction
        existing = await session.execute(
            select(Transaction).where(Transaction.conversation_id == conversation_id)
        )
        if existing.scalar_one_or_none():
            logger.warning(f"Transaction already exists for conversation {conversation_id}")
            return None

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Purchase - Conversation #{conversation_id}",
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url="http://localhost:3000/payment/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="http://localhost:3000/payment/cancel",
            )
        except stripe.StripeError as e:
            logger.error(f"Stripe checkout creation failed: {e}")
            return None

        txn = Transaction(
            conversation_id=conversation_id,
            listing_id=conversation.listing_id,
            buyer_id=conversation.buyer_id,
            amount_cents=amount_cents,
            stripe_checkout_session_id=checkout_session.id,
            checkout_url=checkout_session.url,
            status="pending",
        )
        session.add(txn)
        await session.commit()
        await session.refresh(txn)
        logger.info(f"Created checkout for conversation {conversation_id}: {checkout_session.url}")
        return txn

    @staticmethod
    async def handle_checkout_complete(session: AsyncSession, stripe_session_id: str):
        """Handle Stripe checkout.session.completed webhook."""
        result = await session.execute(
            select(Transaction).where(
                Transaction.stripe_checkout_session_id == stripe_session_id
            )
        )
        txn = result.scalar_one_or_none()
        if not txn:
            logger.error(f"No transaction found for stripe session {stripe_session_id}")
            return

        try:
            stripe_session = stripe.checkout.Session.retrieve(stripe_session_id)
            txn.stripe_payment_intent_id = stripe_session.payment_intent
        except stripe.StripeError as e:
            logger.error(f"Failed to retrieve stripe session: {e}")

        txn.status = "payment_held"
        txn.paid_at = datetime.utcnow()
        txn.updated_at = datetime.utcnow()
        await session.commit()
        logger.info(f"Payment held for transaction {txn.id}")

    @staticmethod
    async def add_tracking(session: AsyncSession, transaction_id: int, tracking_number: str) -> Transaction | None:
        """Add tracking number and mark as shipped."""
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            return None
        if txn.status != "payment_held":
            logger.warning(f"Cannot add tracking to transaction {transaction_id} with status {txn.status}")
            return None

        txn.tracking_number = tracking_number
        txn.status = "shipped"
        txn.shipped_at = datetime.utcnow()
        txn.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(txn)
        logger.info(f"Transaction {transaction_id} shipped with tracking {tracking_number}")
        return txn

    @staticmethod
    async def confirm_delivery(session: AsyncSession, transaction_id: int) -> Transaction | None:
        """Confirm delivery and trigger payout."""
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        txn = result.scalar_one_or_none()
        if not txn or txn.status != "shipped":
            return None

        txn.status = "delivered"
        txn.delivered_at = datetime.utcnow()
        txn.updated_at = datetime.utcnow()
        await session.commit()
        logger.info(f"Transaction {transaction_id} delivered")

        # Trigger payout
        await PaymentService.payout_seller(session, transaction_id)
        await session.refresh(txn)
        return txn

    @staticmethod
    async def payout_seller(session: AsyncSession, transaction_id: int):
        """Transfer funds to seller's connected account."""
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            return

        connected_account_id = settings.stripe_connected_account_id
        if not connected_account_id:
            logger.warning("No connected account configured, skipping payout")
            txn.status = "paid_out"
            txn.paid_out_at = datetime.utcnow()
            txn.updated_at = datetime.utcnow()
            await session.commit()
            return

        try:
            transfer = stripe.Transfer.create(
                amount=txn.amount_cents,
                currency="usd",
                destination=connected_account_id,
                transfer_group=f"conv_{txn.conversation_id}",
            )
            txn.stripe_transfer_id = transfer.id
            txn.status = "paid_out"
            txn.paid_out_at = datetime.utcnow()
            txn.updated_at = datetime.utcnow()
            await session.commit()
            logger.info(f"Payout completed for transaction {transaction_id}: {transfer.id}")
        except stripe.StripeError as e:
            logger.error(f"Payout failed for transaction {transaction_id}: {e}")

    @staticmethod
    async def refund_buyer(session: AsyncSession, transaction_id: int):
        """Refund the buyer's payment."""
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        txn = result.scalar_one_or_none()
        if not txn or not txn.stripe_payment_intent_id:
            return

        try:
            stripe.Refund.create(payment_intent=txn.stripe_payment_intent_id)
            txn.status = "refunded"
            txn.refunded_at = datetime.utcnow()
            txn.updated_at = datetime.utcnow()
            await session.commit()
            logger.info(f"Refund completed for transaction {transaction_id}")
        except stripe.StripeError as e:
            logger.error(f"Refund failed for transaction {transaction_id}: {e}")

    @staticmethod
    async def get_all(session: AsyncSession) -> list[Transaction]:
        """Get all transactions ordered by newest first."""
        result = await session.execute(
            select(Transaction).order_by(Transaction.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_by_id(session: AsyncSession, transaction_id: int) -> Transaction | None:
        """Get a transaction by ID."""
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()
