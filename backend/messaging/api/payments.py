import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_session
from ..config import settings
from ..schemas.payment import TransactionResponse, TrackingUpload, CheckoutResponse
from ..services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/checkout/{conversation_id}", response_model=CheckoutResponse)
async def create_checkout(conversation_id: int, db: AsyncSession = Depends(get_session)):
    txn = await PaymentService.create_checkout(db, conversation_id)
    if not txn:
        raise HTTPException(status_code=400, detail="Could not create checkout session")
    return CheckoutResponse(checkout_url=txn.checkout_url, transaction_id=txn.id)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    webhook_secret = settings.stripe_webhook_secret
    if webhook_secret and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except (ValueError, stripe.SignatureVerificationError) as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        import json
        event = json.loads(payload)

    event_type = event.get("type") if isinstance(event, dict) else event.type

    if event_type == "checkout.session.completed":
        session_data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
        stripe_session_id = session_data.get("id") if isinstance(session_data, dict) else session_data.id

        from database.connection import async_session
        async with async_session() as db:
            await PaymentService.handle_checkout_complete(db, stripe_session_id)

    return {"status": "ok"}


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(db: AsyncSession = Depends(get_session)):
    return await PaymentService.get_all(db)


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: int, db: AsyncSession = Depends(get_session)):
    txn = await PaymentService.get_by_id(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.post("/transactions/{transaction_id}/tracking", response_model=TransactionResponse)
async def add_tracking(
    transaction_id: int,
    body: TrackingUpload,
    db: AsyncSession = Depends(get_session),
):
    txn = await PaymentService.add_tracking(db, transaction_id, body.tracking_number)
    if not txn:
        raise HTTPException(status_code=400, detail="Could not add tracking number")
    return txn
