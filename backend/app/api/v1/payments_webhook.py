"""Stripe webhook receiver for payment events and local simulators."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import get_settings
from app.core.settings import get_payment_settings
from app.integrations import StripeClient, StripeClientError
from app.models import PaymentEvent, PaymentTransaction, PaymentTransactionStatus
from app.services import payments_service

router = APIRouter(prefix="/payments", tags=["payments-webhook"])


def _as_decimal_cents(value: Any) -> Decimal | None:
    """Convert Stripe integer-cent values to Decimal dollars."""

    if value is None:
        return None
    try:
        cents = Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None
    return cents / Decimal("100")


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


async def _process_event(
    session: AsyncSession,
    payload: dict[str, Any],
    *,
    record_event: bool = True,
) -> dict[str, Any]:
    event_id = str(payload.get("id") or uuid4())
    event_type = payload.get("type", "")
    data_object = payload.get("data", {}).get("object", {})

    status_payload = "ignored"

    if event_type == "payment_intent.succeeded":
        payment_intent_id = data_object.get("id")
        transaction = await _get_transaction_by_intent(session, str(payment_intent_id))
        if transaction is not None:
            await payments_service.mark_invoice_paid_on_success(
                session,
                invoice_id=transaction.invoice_id,
                transaction_id=transaction.id,
            )
        status_payload = "processed"

    elif event_type == "payment_intent.payment_failed":
        payment_intent_id = data_object.get("id")
        reason = (data_object.get("last_payment_error", {}) or {}).get("message")
        transaction = await _get_transaction_by_intent(session, str(payment_intent_id))
        if transaction is not None:
            transaction.status = PaymentTransactionStatus.FAILED
            transaction.failure_reason = reason
            await session.commit()
        status_payload = "processed"

    elif event_type == "charge.refunded":
        payment_intent_id = data_object.get("payment_intent")
        amount_decimal = _as_decimal_cents(data_object.get("amount_refunded"))
        transaction = await _get_transaction_by_intent(session, str(payment_intent_id))
        if transaction is not None:
            await payments_service.apply_refund_markers(
                session,
                invoice_id=transaction.invoice_id,
                transaction_id=transaction.id,
                amount=amount_decimal,
            )
        status_payload = "processed"

    if record_event:
        await _record_event(session, event_id, payload)

    return {"status": status_payload}


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_webhook(
    request: Request,
    session: AsyncSession = Depends(deps.get_db_session),
    stripe_client: StripeClient = Depends(deps.get_stripe_client),
) -> dict[str, Any]:
    settings = get_payment_settings()
    payload_bytes = await request.body()
    payload: dict[str, Any]

    if settings.payments_webhook_verify:
        signature = request.headers.get("Stripe-Signature")
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing signature header",
            )
        try:  # pragma: no cover - depends on stripe availability
            event = stripe_client.construct_event(payload_bytes, signature)
        except StripeClientError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        if hasattr(event, "to_dict_recursive"):
            payload = cast(dict[str, Any], event.to_dict_recursive())
        else:
            payload = cast(dict[str, Any], event)
    else:
        try:
            payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload"
            ) from exc

    return await _process_event(session, payload)


@router.post("/dev/simulate-webhook", status_code=status.HTTP_200_OK)
async def simulate_webhook(
    payload: dict[str, Any] = Body(...),
    session: AsyncSession = Depends(deps.get_db_session),
) -> dict[str, Any]:
    settings = get_settings()
    if settings.app_env.lower() != "local":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulation route available in local environment only",
        )

    enriched_payload = dict(payload)
    enriched_payload.setdefault("id", f"simulated_{uuid4().hex}")
    return await _process_event(session, enriched_payload, record_event=True)
