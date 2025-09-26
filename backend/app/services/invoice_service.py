"""Invoice creation, totals, and payment utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Final
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Deposit,
    DepositStatus,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Pet,
    Reservation,
)
from app.services import pricing_service

_MONEY_PLACES: Final = Decimal("0.01")


def _to_money(value: Decimal | float | str) -> Decimal:
    """Normalize numeric values to a money-safe decimal."""

    return Decimal(value).quantize(_MONEY_PLACES, rounding=ROUND_HALF_UP)


@dataclass(slots=True)
class InvoiceTotals:
    """Representation of invoice totals."""

    invoice_id: UUID
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal


async def create_from_reservation(
    session: AsyncSession,
    *,
    reservation_id: UUID,
    account_id: UUID,
    promotion_code: str | None = None,
) -> UUID:
    """Create an invoice populated with pricing line items."""

    reservation = await _load_reservation(session, reservation_id, account_id)
    if reservation is None:
        raise ValueError("Reservation not found")

    if reservation.invoice is not None:
        raise ValueError("Reservation already has an invoice")

    quote = await pricing_service.quote_reservation(
        session,
        reservation_id=reservation.id,
        account_id=account_id,
        promotion_code=promotion_code,
    )

    invoice = Invoice(
        account_id=account_id,
        reservation_id=reservation.id,
        subtotal=quote.subtotal,
        discount_total=quote.discount_total,
        tax_total=quote.tax_total,
        total=quote.total,
        total_amount=quote.total,
    )
    session.add(invoice)
    await session.flush()

    session.add_all(
        [
            InvoiceItem(
                invoice_id=invoice.id,
                description=line.description,
                amount=line.amount,
            )
            for line in quote.items
        ]
    )
    await session.commit()
    await session.refresh(invoice, attribute_names=["items"])
    return invoice.id


async def compute_totals(
    session: AsyncSession,
    *,
    invoice_id: UUID,
    account_id: UUID,
    promotion_code: str | None = None,
) -> InvoiceTotals:
    """Recalculate invoice totals using pricing rules and optional promotion."""

    invoice = await _load_invoice(session, invoice_id, account_id)
    if invoice is None:
        raise ValueError("Invoice not found")

    quote = await pricing_service.quote_reservation(
        session,
        reservation_id=invoice.reservation_id,
        account_id=account_id,
        promotion_code=promotion_code,
    )

    invoice.items.clear()
    await session.flush()
    session.add_all(
        [
            InvoiceItem(
                invoice_id=invoice.id,
                description=line.description,
                amount=line.amount,
            )
            for line in quote.items
        ]
    )

    invoice.subtotal = quote.subtotal
    invoice.discount_total = quote.discount_total
    invoice.tax_total = quote.tax_total
    invoice.total = quote.total
    invoice.total_amount = quote.total
    await session.commit()
    await session.refresh(invoice)

    return InvoiceTotals(
        invoice_id=invoice.id,
        subtotal=invoice.subtotal,
        discount_total=invoice.discount_total,
        tax_total=invoice.tax_total,
        total=invoice.total,
    )


async def amount_due(
    session: AsyncSession,
    *,
    invoice_id: UUID,
    account_id: UUID,
) -> Decimal:
    """Return the remaining balance for an invoice after held deposits."""

    invoice = await _load_invoice(session, invoice_id, account_id)
    if invoice is None:
        raise ValueError("Invoice not found")

    total = (invoice.total or Decimal("0")).quantize(_MONEY_PLACES)
    held_raw = await session.scalar(
        select(func.coalesce(func.sum(Deposit.amount), 0)).where(
            Deposit.reservation_id == invoice.reservation_id,
            Deposit.account_id == account_id,
            Deposit.status == DepositStatus.HELD,
        )
    )
    held = Decimal(held_raw or 0).quantize(_MONEY_PLACES)
    due = total - held
    if due <= Decimal("0"):
        return Decimal("0.00")
    return due.quantize(_MONEY_PLACES)


async def invoice_paid(
    session: AsyncSession,
    *,
    invoice_id: UUID,
    account_id: UUID,
) -> Invoice:
    """Mark an invoice as paid and return the hydrated invoice."""

    invoice = await _load_invoice(session, invoice_id, account_id)
    if invoice is None:
        raise ValueError("Invoice not found")
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(invoice)
    return invoice


async def settle_deposit(
    session: AsyncSession,
    *,
    reservation_id: UUID,
    account_id: UUID,
    action: str,
    amount: Decimal,
) -> Deposit:
    """Transition a deposit through its lifecycle."""

    action_normalized = action.lower()
    try:
        status = {
            "hold": DepositStatus.HELD,
            "consume": DepositStatus.CONSUMED,
            "refund": DepositStatus.REFUNDED,
            "forfeit": DepositStatus.FORFEITED,
        }[action_normalized]
    except KeyError as exc:
        raise ValueError("Unsupported deposit action") from exc

    reservation = await _load_reservation(session, reservation_id, account_id)
    if reservation is None:
        raise ValueError("Reservation not found")

    owner = reservation.pet.owner if reservation.pet else None
    if owner is None:
        raise ValueError("Reservation is missing owner")

    normalized_amount = _to_money(amount)
    if normalized_amount <= 0:
        raise ValueError("Deposit amount must be positive")

    if status is DepositStatus.HELD:
        existing = await _get_active_deposit(session, reservation_id, account_id)
        if existing is not None:
            raise ValueError("Deposit already held")
        deposit = Deposit(
            account_id=account_id,
            reservation_id=reservation_id,
            owner_id=owner.id,
            amount=normalized_amount,
            status=status,
        )
        session.add(deposit)
    else:
        existing = await _get_active_deposit(session, reservation_id, account_id)
        if existing is None:
            raise ValueError("No held deposit to settle")
        existing.status = status
        existing.amount = normalized_amount
        deposit = existing

    await session.commit()
    await session.refresh(deposit)
    return deposit


async def _load_reservation(
    session: AsyncSession,
    reservation_id: UUID,
    account_id: UUID,
) -> Reservation | None:
    stmt: Select[tuple[Reservation]] = (
        select(Reservation)
        .options(
            selectinload(Reservation.pet).selectinload(Pet.owner),
            selectinload(Reservation.deposits),
            selectinload(Reservation.invoice),
        )
        .where(
            Reservation.id == reservation_id,
            Reservation.account_id == account_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def _load_invoice(
    session: AsyncSession,
    invoice_id: UUID,
    account_id: UUID,
) -> Invoice | None:
    stmt = (
        select(Invoice)
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.reservation)
            .selectinload(Reservation.pet)
            .selectinload(Pet.owner),
            selectinload(Invoice.reservation).selectinload(Reservation.deposits),
        )
        .where(Invoice.id == invoice_id, Invoice.account_id == account_id)
    )
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def _get_active_deposit(
    session: AsyncSession,
    reservation_id: UUID,
    account_id: UUID,
) -> Deposit | None:
    stmt = select(Deposit).where(
        Deposit.reservation_id == reservation_id,
        Deposit.account_id == account_id,
        Deposit.status == DepositStatus.HELD,
    )
    result = await session.execute(stmt)
    return result.scalars().one_or_none()
