"""Store credit ledger operations and invoice integration."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Final
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CreditApplication,
    CreditApplicationType,
    Invoice,
    OwnerProfile,
    Reservation,
    Pet,
    StoreCreditLedger,
    StoreCreditSource,
)

_CURRENCY_UNIT: Final = Decimal("0.01")
_ROUNDING_MODE: Final = ROUND_HALF_UP


def _to_money(value: Decimal | float | str) -> Decimal:
    return Decimal(value).quantize(_CURRENCY_UNIT, rounding=_ROUNDING_MODE)


async def add_credit(
    session: AsyncSession,
    *,
    account_id: UUID,
    owner_id: UUID,
    amount: Decimal,
    source: StoreCreditSource,
    note: str | None = None,
    invoice_id: UUID | None = None,
) -> StoreCreditLedger:
    """Credit an owner's ledger with the provided amount."""

    normalized = _to_money(amount)
    if normalized <= Decimal("0"):
        raise ValueError("Store credit amount must be positive")

    owner = await _load_owner(session, owner_id)
    if owner is None or owner.user is None:
        raise ValueError("Owner not found")
    if owner.user.account_id != account_id:
        raise ValueError("Owner does not belong to account")

    entry = StoreCreditLedger(
        account_id=account_id,
        owner_id=owner_id,
        amount=normalized,
        source=source,
        note=note,
        invoice_id=invoice_id,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def owner_balance(
    session: AsyncSession,
    *,
    account_id: UUID,
    owner_id: UUID,
) -> Decimal:
    """Return the current store credit balance for an owner."""

    owner = await _load_owner(session, owner_id)
    if owner is None or owner.user is None or owner.user.account_id != account_id:
        raise ValueError("Owner not found")

    balance = await session.scalar(
        select(func.coalesce(func.sum(StoreCreditLedger.amount), 0)).where(
            StoreCreditLedger.account_id == account_id,
            StoreCreditLedger.owner_id == owner_id,
        )
    )
    return _to_money(balance or Decimal("0"))


async def apply_store_credit(
    session: AsyncSession,
    *,
    invoice_id: UUID,
    account_id: UUID,
    owner_id: UUID,
    amount: Decimal,
) -> Decimal:
    """Apply store credit to an invoice and return the applied amount."""

    invoice = await _load_invoice(session, invoice_id, account_id)
    if invoice is None:
        raise ValueError("Invoice not found")

    reservation = invoice.reservation
    if reservation is None or reservation.pet is None or reservation.pet.owner is None:
        raise ValueError("Invoice reservation missing owner")
    invoice_owner = reservation.pet.owner
    if invoice_owner.id != owner_id:
        raise ValueError("Invoice does not belong to the owner")

    current_balance = await owner_balance(
        session, account_id=account_id, owner_id=owner_id
    )
    if current_balance <= Decimal("0"):
        raise ValueError("Owner has no store credit available")

    requested = _to_money(amount)
    if requested <= Decimal("0"):
        raise ValueError("Credit application amount must be positive")

    amount_due = _invoice_balance(invoice)
    if amount_due <= Decimal("0"):
        raise ValueError("Invoice balance is already zero")

    apply_amount = min(requested, current_balance, amount_due)
    if apply_amount <= Decimal("0"):
        raise ValueError("No store credit could be applied")

    session.add(
        CreditApplication(
            account_id=account_id,
            invoice_id=invoice.id,
            type=CreditApplicationType.STORE_CREDIT,
            reference_id=owner_id,
            amount=apply_amount,
        )
    )
    session.add(
        StoreCreditLedger(
            account_id=account_id,
            owner_id=owner_id,
            amount=-apply_amount,
            source=StoreCreditSource.CONSUME,
            invoice_id=invoice.id,
            note=f"Applied to invoice {invoice.id}",
        )
    )

    invoice.credits_total = _to_money(
        (invoice.credits_total or Decimal("0")) + apply_amount
    )
    invoice.total_amount = _remaining_total(invoice.total, invoice.credits_total)

    await session.commit()
    await session.refresh(invoice, attribute_names=["credits_total", "total_amount"])
    return apply_amount


def _invoice_balance(invoice: Invoice) -> Decimal:
    total = _to_money(invoice.total or Decimal("0"))
    credits = _to_money(invoice.credits_total or Decimal("0"))
    balance = total - credits
    return balance if balance > Decimal("0") else Decimal("0.00")


def _remaining_total(total: Decimal | None, credits: Decimal | None) -> Decimal:
    total_value = _to_money(total or Decimal("0"))
    credits_value = _to_money(credits or Decimal("0"))
    remainder = total_value - credits_value
    return remainder if remainder > Decimal("0") else Decimal("0.00")


async def _load_owner(session: AsyncSession, owner_id: UUID) -> OwnerProfile | None:
    stmt = (
        select(OwnerProfile)
        .where(OwnerProfile.id == owner_id)
        .options(selectinload(OwnerProfile.user))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_invoice(
    session: AsyncSession, invoice_id: UUID, account_id: UUID
) -> Invoice | None:
    stmt = (
        select(Invoice)
        .options(
            selectinload(Invoice.reservation)
            .selectinload(Reservation.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.user),
            selectinload(Invoice.credit_applications),
        )
        .where(Invoice.id == invoice_id, Invoice.account_id == account_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
