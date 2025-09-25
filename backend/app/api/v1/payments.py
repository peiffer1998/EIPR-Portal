"""Stripe payment endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.integrations import StripeClient, StripeClientError
from app.models.invoice import InvoiceStatus
from app.models.user import User, UserRole
from app.schemas.invoice import InvoiceRead
from app.schemas.payment import (
    PaymentIntentConfirm,
    PaymentIntentCreate,
    PaymentIntentRead,
    WebhookAck,
)
from app.services import billing_service, invoice_service, notification_service

router = APIRouter()


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.post(
    "/create-intent",
    response_model=PaymentIntentRead,
    summary="Create a Stripe payment intent",
)
async def create_payment_intent(
    payload: PaymentIntentCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    stripe_client: Annotated[StripeClient, Depends(deps.get_stripe_client)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PaymentIntentRead:
    _assert_staff(current_user)
    invoice = await billing_service.get_invoice(
        session, account_id=current_user.account_id, invoice_id=payload.invoice_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice already paid"
        )
    if payload.amount < invoice.total_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Amount less than total"
        )

    try:
        intent = stripe_client.create_payment_intent(
            amount=payload.amount,
            invoice_id=invoice.id,
            metadata={"account_id": str(invoice.account_id)},
        )
    except StripeClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return PaymentIntentRead(
        payment_intent_id=intent.id,
        client_secret=intent.client_secret,
        status=intent.status,
        invoice_id=payload.invoice_id,
    )


@router.post(
    "/confirm",
    response_model=InvoiceRead,
    summary="Confirm a Stripe payment intent",
)
async def confirm_payment_intent(
    payload: PaymentIntentConfirm,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    stripe_client: Annotated[StripeClient, Depends(deps.get_stripe_client)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
) -> InvoiceRead:
    _assert_staff(current_user)
    try:
        intent = stripe_client.confirm_payment_intent(payload.payment_intent_id)
    except StripeClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    invoice_id_raw = intent.metadata.get("invoice_id")
    if not invoice_id_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing invoice metadata"
        )
    try:
        invoice_id = uuid.UUID(invoice_id_raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invoice id"
        ) from exc

    invoice = await billing_service.get_invoice(
        session, account_id=current_user.account_id, invoice_id=invoice_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    updated = await billing_service.mark_invoice_paid(
        session, invoice=invoice, account_id=current_user.account_id
    )
    await invoice_service.consume_reservation_deposits(
        session,
        account_id=current_user.account_id,
        reservation_id=invoice.reservation_id,
    )

    notification_service.notify_payment_receipt(updated, background_tasks)
    return InvoiceRead.model_validate(updated)


@router.post("/webhook", response_model=WebhookAck, summary="Receive Stripe webhooks")
async def stripe_webhook(  # pragma: no cover - exercised via integration tests
    request: Request,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    stripe_client: Annotated[StripeClient, Depends(deps.get_stripe_client)],
) -> WebhookAck:
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe_client.construct_event(payload, signature)
    except StripeClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    event_type = event.get("type")
    if event_type == "payment_intent.succeeded":
        data = event.get("data", {}).get("object", {})
        metadata = data.get("metadata", {})
        invoice_id_raw = metadata.get("invoice_id")
        account_id_raw = metadata.get("account_id")
        if invoice_id_raw and account_id_raw:
            try:
                invoice_id = uuid.UUID(invoice_id_raw)
                account_id = uuid.UUID(account_id_raw)
            except ValueError:
                invoice_id = None
                account_id = None
            if invoice_id and account_id:
                invoice = await billing_service.get_invoice(
                    session, account_id=account_id, invoice_id=invoice_id
                )
                if invoice is not None and invoice.status != InvoiceStatus.PAID:
                    await billing_service.mark_invoice_paid(
                        session, invoice=invoice, account_id=account_id
                    )
                    await invoice_service.consume_reservation_deposits(
                        session,
                        account_id=account_id,
                        reservation_id=invoice.reservation_id,
                    )
    return WebhookAck(received=True)
