"""Payments API endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.integrations import stripe_client
from app.models import PaymentTransaction
from app.models.user import User, UserRole
from app.schemas.payments import (
    PaymentIntentCreateRequest,
    PaymentIntentCreateResponse,
    PaymentRefundRequest,
    PaymentRefundResponse,
)
from app.services import billing_service, payments_service

router = APIRouter(prefix="/payments", tags=["payments"])


def _ensure_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


@router.post("/create-intent", response_model=PaymentIntentCreateResponse)
async def create_payment_intent(
    payload: PaymentIntentCreateRequest,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> PaymentIntentCreateResponse:
    invoice = await billing_service.get_invoice(
        session,
        account_id=current_user.account_id,
        invoice_id=payload.invoice_id,
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    if current_user.role == UserRole.PET_PARENT:
        reservation = invoice.reservation
        owner_profile = getattr(getattr(reservation, "pet", None), "owner", None)
        if owner_profile is None or owner_profile.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
    amount = invoice.total
    if amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice has no total"
        )

    (
        client_secret,
        transaction_id,
    ) = await payments_service.create_or_update_payment_for_invoice(
        session,
        account_id=current_user.account_id,
        invoice_id=payload.invoice_id,
        amount=Decimal(amount),
    )

    return PaymentIntentCreateResponse(
        client_secret=client_secret,
        transaction_id=transaction_id,
    )


@router.post("/refund", response_model=PaymentRefundResponse)
async def refund_payment(
    payload: PaymentRefundRequest,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> PaymentRefundResponse:
    _ensure_staff(current_user)

    invoice = await billing_service.get_invoice(
        session,
        account_id=current_user.account_id,
        invoice_id=payload.invoice_id,
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
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
    refund_result = stripe_client.refund_charge(
        transaction.provider_payment_intent_id,
        amount=amount,
    )

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
