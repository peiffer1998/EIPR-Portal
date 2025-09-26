"""Payments API integrating Stripe intents with local transaction records."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.integrations import StripeClient, StripeClientError
from app.models import InvoiceStatus, PaymentTransaction
from app.models.user import User, UserRole
from app.schemas.invoice import InvoiceRead
from app.schemas.payment import PaymentIntentConfirm
from app.schemas.payments import (
    PaymentIntentCreateRequest,
    PaymentIntentCreateResponse,
    PaymentRefundRequest,
    PaymentRefundResponse,
)
from app.services import billing_service, notification_service, payments_service

router = APIRouter(prefix="/payments", tags=["payments"])


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.post("/create-intent", response_model=PaymentIntentCreateResponse)
async def create_payment_intent(
    payload: PaymentIntentCreateRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    stripe_client: Annotated[StripeClient, Depends(deps.get_stripe_client)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PaymentIntentCreateResponse:
    invoice = await billing_service.get_invoice(
        session, account_id=current_user.account_id, invoice_id=payload.invoice_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    # Pet-parents may only create intents for their own invoice
    if current_user.role == UserRole.PET_PARENT:
        reservation = invoice.reservation
        owner_profile = getattr(getattr(reservation, "pet", None), "owner", None)
        if owner_profile is None or owner_profile.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )

    try:
        (
            client_secret,
            transaction_id,
        ) = await payments_service.create_or_update_payment_for_invoice(
            session,
            account_id=current_user.account_id,
            invoice_id=payload.invoice_id,
            stripe=stripe_client,
        )
    except StripeClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    if client_secret is None:
        invoice = await billing_service.get_invoice(
            session,
            account_id=current_user.account_id,
            invoice_id=payload.invoice_id,
        )
        return PaymentIntentCreateResponse(
            client_secret=None,
            transaction_id=None,
            invoice_status=invoice.status.value if invoice else None,
            message="Invoice already settled; no payment required.",
        )

    return PaymentIntentCreateResponse(
        client_secret=client_secret,
        transaction_id=transaction_id,
    )


@router.post(
    "/confirm",
    response_model=InvoiceRead,
    summary="Confirm a payment intent and finalize the invoice",
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

    stmt = select(PaymentTransaction).where(
        PaymentTransaction.provider_payment_intent_id == payload.payment_intent_id
    )
    transaction = (await session.execute(stmt)).scalars().first()

    if transaction is not None:
        await payments_service.mark_invoice_paid_on_success(
            session,
            invoice_id=transaction.invoice_id,
            transaction_id=transaction.id,
        )
        invoice = await billing_service.get_invoice(
            session,
            account_id=current_user.account_id,
            invoice_id=invoice_id,
        )
    else:
        invoice = await billing_service.mark_invoice_paid(
            session, invoice=invoice, account_id=current_user.account_id
        )

    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    notification_service.notify_payment_receipt(invoice, background_tasks)
    return InvoiceRead.model_validate(invoice)


@router.post("/refund", response_model=PaymentRefundResponse)
async def refund_payment(
    payload: PaymentRefundRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    stripe_client: Annotated[StripeClient, Depends(deps.get_stripe_client)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> PaymentRefundResponse:
    _assert_staff(current_user)

    invoice = await billing_service.get_invoice(
        session,
        account_id=current_user.account_id,
        invoice_id=payload.invoice_id,
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    if invoice.status != InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice must be paid before requesting a refund",
        )

    stmt = (
        select(PaymentTransaction)
        .where(
            PaymentTransaction.invoice_id == payload.invoice_id,
            PaymentTransaction.provider == "stripe",
        )
        .order_by(PaymentTransaction.created_at.desc())
    )
    transaction = (await session.execute(stmt)).scalars().first()
    if transaction is None or not transaction.provider_payment_intent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No payment intent available for refund",
        )

    amount = (
        payload.amount.quantize(Decimal("0.01")) if payload.amount is not None else None
    )
    try:
        refund_result = stripe_client.refund_payment_intent(
            transaction.provider_payment_intent_id,
            amount=amount,
        )
    except StripeClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    await payments_service.apply_refund_markers(
        session,
        invoice_id=payload.invoice_id,
        transaction_id=transaction.id,
        amount=amount,
    )

    raw_amount = refund_result.get("amount")
    response_amount: Decimal | None = amount
    if raw_amount is not None:
        response_amount = Decimal(raw_amount) / Decimal("100")

    return PaymentRefundResponse(
        status=str(refund_result.get("status", "unknown")),
        amount=response_amount,
    )
