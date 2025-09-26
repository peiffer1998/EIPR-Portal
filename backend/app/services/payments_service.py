"""Service layer for handling payments and transactions."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations import StripeClient
from app.models import (
    DepositStatus,
    Invoice,
    OwnerProfile,
    PaymentTransaction,
    PaymentTransactionStatus,
    Pet,
    Reservation,
)
from app.services import invoice_service

_STATUS_MAP: Mapping[str, PaymentTransactionStatus] = {
    "requires_payment_method": PaymentTransactionStatus.REQUIRES_PAYMENT_METHOD,
    "requires_confirmation": PaymentTransactionStatus.REQUIRES_CONFIRMATION,
    "processing": PaymentTransactionStatus.PROCESSING,
    "succeeded": PaymentTransactionStatus.SUCCEEDED,
    "canceled": PaymentTransactionStatus.CANCELED,
    "failed": PaymentTransactionStatus.FAILED,
    "refunded": PaymentTransactionStatus.REFUNDED,
    "partial_refund": PaymentTransactionStatus.PARTIAL_REFUND,
}


def _to_status(status: str) -> PaymentTransactionStatus:
    return _STATUS_MAP.get(status, PaymentTransactionStatus.PROCESSING)


async def _get_invoice(
    session: AsyncSession,
    *,
    account_id: UUID,
    invoice_id: UUID,
) -> Invoice:
    stmt = (
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.account_id == account_id)
        .options(
            selectinload(Invoice.reservation)
            .selectinload(Reservation.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.user),
            selectinload(Invoice.reservation).selectinload(Reservation.deposits),
        )
    )
    result = await session.execute(stmt)
    invoice = result.scalars().unique().one_or_none()
    if invoice is None:
        raise ValueError("Invoice not found for account")
    return invoice


async def create_or_update_payment_for_invoice(
    session: AsyncSession,
    *,
    account_id: UUID,
    invoice_id: UUID,
    currency: str = "usd",
    stripe: StripeClient,
) -> tuple[str, UUID]:
    """Create or refresh a PaymentIntent and persist a transaction."""

    invoice = await _get_invoice(session, account_id=account_id, invoice_id=invoice_id)
    if invoice.reservation is None or invoice.reservation.pet is None:
        raise ValueError("Invoice is missing reservation context")
    owner_profile = invoice.reservation.pet.owner
    if owner_profile is None or owner_profile.user is None:
        raise ValueError("Invoice is missing owner information")

    amount_due = await invoice_service.amount_due(
        session, invoice_id=invoice_id, account_id=account_id
    )
    if amount_due <= Decimal("0"):
        raise ValueError("Invoice balance is zero; no payment required")
    customer_email = owner_profile.user.email
    idempotency_key = f"invoice-{invoice_id}-intent"
    intent = stripe.create_payment_intent(
        amount=amount_due,
        invoice_id=invoice_id,
        currency=currency,
        metadata={"account_id": str(account_id)},
        customer_email=customer_email,
        idempotency_seed=idempotency_key,
    )
    if intent.client_secret is None:
        raise ValueError("Stripe did not return a client secret")

    stmt = (
        select(PaymentTransaction)
        .where(
            PaymentTransaction.invoice_id == invoice_id,
            PaymentTransaction.provider == "stripe",
        )
        .order_by(PaymentTransaction.created_at.desc())
    )
    existing = (await session.execute(stmt)).scalars().first()

    status = _to_status(intent.status)
    normalized_amount = amount_due.quantize(Decimal("0.01"))
    if existing is None:
        transaction = PaymentTransaction(
            account_id=account_id,
            invoice_id=invoice_id,
            owner_id=owner_profile.id,
            provider="stripe",
            provider_payment_intent_id=intent.id,
            amount=normalized_amount,
            currency=currency,
            status=status,
            failure_reason=None,
        )
        session.add(transaction)
        await session.flush()
    else:
        existing.provider_payment_intent_id = intent.id
        existing.amount = normalized_amount
        existing.currency = currency
        existing.status = status
        existing.failure_reason = None
        transaction = existing

    await session.commit()
    return intent.client_secret, transaction.id


async def mark_invoice_paid_on_success(
    session: AsyncSession,
    *,
    invoice_id: UUID,
    transaction_id: UUID,
) -> None:
    """Mark invoice and transaction as succeeded."""

    transaction = await session.get(PaymentTransaction, transaction_id)
    if transaction is None or transaction.invoice_id != invoice_id:
        raise ValueError("Transaction not found for invoice")

    transaction.status = PaymentTransactionStatus.SUCCEEDED
    transaction.failure_reason = None

    invoice = await _get_invoice(
        session, account_id=transaction.account_id, invoice_id=invoice_id
    )
    reservation = invoice.reservation
    if reservation is not None:
        for deposit in reservation.deposits:
            if deposit.status == DepositStatus.HELD:
                deposit.status = DepositStatus.CONSUMED

    await invoice_service.invoice_paid(
        session, invoice_id=invoice_id, account_id=transaction.account_id
    )
    await session.refresh(transaction)


async def apply_refund_markers(
    session: AsyncSession,
    *,
    invoice_id: UUID,
    transaction_id: UUID,
    amount: Decimal | None = None,
) -> None:
    """Update transaction records following a refund."""

    transaction = await session.get(PaymentTransaction, transaction_id)
    if transaction is None or transaction.invoice_id != invoice_id:
        raise ValueError("Transaction not found for invoice")

    if amount is None or amount >= transaction.amount:
        transaction.status = PaymentTransactionStatus.REFUNDED
    else:
        transaction.status = PaymentTransactionStatus.PARTIAL_REFUND
    transaction.failure_reason = None

    await session.commit()
