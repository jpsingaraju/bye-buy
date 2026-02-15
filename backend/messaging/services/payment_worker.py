import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from database.connection import async_session
from ..models.transaction import Transaction
from .payment_service import PaymentService

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds
DELIVERY_DELAY = 30  # seconds (dummy: marks delivered after 30s)
REFUND_DEADLINE_DAYS = 7


class PaymentWorker:
    """Background worker that monitors shipments and handles auto-delivery/refunds."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Payment worker started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Payment worker stopped")

    async def _run(self):
        while self._running:
            try:
                await self._check_deliveries()
                await self._check_refunds()
            except Exception as e:
                logger.error(f"Payment worker error: {e}")
            await asyncio.sleep(POLL_INTERVAL)

    async def _check_deliveries(self):
        """Auto-confirm delivery for shipped transactions after DELIVERY_DELAY seconds."""
        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(seconds=DELIVERY_DELAY)
            result = await session.execute(
                select(Transaction)
                .where(Transaction.status == "shipped")
                .where(Transaction.shipped_at <= cutoff)
            )
            transactions = result.scalars().all()

            for txn in transactions:
                logger.info(f"Auto-confirming delivery for transaction {txn.id}")
                await PaymentService.confirm_delivery(session, txn.id)

    async def _check_refunds(self):
        """Auto-refund if no tracking uploaded within REFUND_DEADLINE_DAYS of payment."""
        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=REFUND_DEADLINE_DAYS)
            result = await session.execute(
                select(Transaction)
                .where(Transaction.status == "payment_held")
                .where(Transaction.paid_at <= cutoff)
            )
            transactions = result.scalars().all()

            for txn in transactions:
                logger.info(f"Auto-refunding transaction {txn.id} (no tracking after {REFUND_DEADLINE_DAYS} days)")
                await PaymentService.refund_buyer(session, txn.id)


payment_worker = PaymentWorker()
