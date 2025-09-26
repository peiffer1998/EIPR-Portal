"""Stripe webhook receiver for payment events."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.settings import get_payment_settings
from app.integrations import stripe_client
from app.models import PaymentEvent, PaymentTransaction, PaymentTransactionStatus
from app.services import payments_service

router = APIRouter(prefix="/payments", tags=["payments-webhook"])


async def _record_event(
    session: AsyncSession, event_id: str, payload: dict[str, Any]
) -> None:
    if not event_id:
        return
    session.add(PaymentEvent(provider_event_id=event_id, raw=payload))
    try:
        await session.commit()
    except IntegrityError:  # duplicate events are ignored
        await session.rollback()


async def _get_transaction_by_intent(
    session: AsyncSession, payment_intent_id: str
) -> PaymentTransaction | None:
    if not payment_intent_id:
        return None
    stmt = select(PaymentTransaction).where(
        PaymentTransaction.provider_payment_intent_id == payment_intent_id
    )
    return (await session.execute(stmt)).scalars().first()


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_webhook(
    request: Request,
    session: AsyncSession = Depends(deps.get_db_session),
) -> dict[str, Any]:
    settings = get_payment_settings()
    payload_bytes = await request.body()
    payload: dict[str, Any]

    if settings.payments_webhook_verify:
        if stripe_client.stripe is None or not settings.stripe_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe verification unavailable",
            )
        signature = request.headers.get("Stripe-Signature")
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing signature header",
            )
        try:  # pragma: no cover - depends on stripe availability
            event = stripe_client.stripe.Webhook.construct_event(  # type: ignore[attr-defined]
                payload_bytes.decode("utf-8"),
                signature,
                settings.stripe_webhook_secret,
            )
            payload = event.to_dict_recursive()
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature"
            ) from exc
    else:
        try:
            payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload"
            ) from exc

    event_id = str(payload.get("id", ""))
    event_type = payload.get("type", "")
    data_object = payload.get("data", {}).get("object", {})

    if event_type == "payment_intent.succeeded":
        payment_intent_id = data_object.get("id")
        transaction = await _get_transaction_by_intent(session, str(payment_intent_id))
        if transaction is not None:
            await payments_service.mark_invoice_paid_on_success(
                session,
                invoice_id=transaction.invoice_id,
                transaction_id=transaction.id,
            )
        await _record_event(session, event_id, payload)
        return {"status": "processed"}

    if event_type == "payment_intent.payment_failed":
        payment_intent_id = data_object.get("id")
        reason = (data_object.get("last_payment_error", {}) or {}).get("message")
        transaction = await _get_transaction_by_intent(session, str(payment_intent_id))
        if transaction is not None:
            transaction.status = PaymentTransactionStatus.FAILED
            transaction.failure_reason = reason
            await session.commit()
        await _record_event(session, event_id, payload)
        return {"status": "processed"}

    if event_type == "charge.refunded":
        payment_intent_id = data_object.get("payment_intent")
        amount_cents = data_object.get("amount_refunded")
        amount_decimal = (
            Decimal(amount_cents) / Decimal("100")
            if isinstance(amount_cents, (int, float))
            else None
        )
        transaction = await _get_transaction_by_intent(session, str(payment_intent_id))
        if transaction is not None:
            await payments_service.apply_refund_markers(
                session,
                invoice_id=transaction.invoice_id,
                transaction_id=transaction.id,
                amount=amount_decimal,
            )
        await _record_event(session, event_id, payload)
        return {"status": "processed"}

    await _record_event(session, event_id, payload)
    return {"status": "ignored"}
