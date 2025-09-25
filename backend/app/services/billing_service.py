"""Billing services for invoices."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.reservation import Reservation
from app.schemas.invoice import InvoiceItemCreate


async def _ensure_reservation(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> Reservation:
    reservation = await session.get(
        Reservation,
        reservation_id,
        options=[selectinload(Reservation.invoice).selectinload(Invoice.items)],
    )
    if reservation is None or reservation.account_id != account_id:
        raise ValueError("Reservation not found for account")
    return reservation


async def list_invoices(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    status: InvoiceStatus | None = None,
) -> list[Invoice]:
    stmt: Select[tuple[Invoice]] = select(Invoice).where(Invoice.account_id == account_id)
    if status is not None:
        stmt = stmt.where(Invoice.status == status)
    stmt = stmt.options(selectinload(Invoice.items)).order_by(Invoice.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_invoice(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Invoice | None:
    stmt = (
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.account_id == account_id)
        .options(selectinload(Invoice.items))
    )
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def generate_invoice_for_reservation(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> Invoice:
    reservation = await _ensure_reservation(
        session, account_id=account_id, reservation_id=reservation_id
    )
    if reservation.invoice is not None:
        raise ValueError("Invoice already exists for reservation")

    invoice = Invoice(
        account_id=account_id,
        reservation_id=reservation_id,
        status=InvoiceStatus.PENDING,
    )
    base_item = InvoiceItem(
        description="Reservation base rate",
        amount=reservation.base_rate,
    )
    invoice.items.append(base_item)
    invoice.total_amount = reservation.base_rate

    session.add(invoice)
    await session.commit()
    await session.refresh(invoice, attribute_names=["items"])
    return invoice


async def add_invoice_item(
    session: AsyncSession,
    *,
    invoice: Invoice,
    account_id: uuid.UUID,
    payload: InvoiceItemCreate,
) -> Invoice:
    if invoice.account_id != account_id:
        raise ValueError("Invoice does not belong to the provided account")
    invoice.items.append(
        InvoiceItem(description=payload.description, amount=payload.amount)
    )
    await _recalculate_total(session, invoice)
    await session.commit()
    await session.refresh(invoice, attribute_names=["items"])
    return invoice


async def mark_invoice_paid(
    session: AsyncSession,
    *,
    invoice: Invoice,
    account_id: uuid.UUID,
    paid_at: datetime | None = None,
) -> Invoice:
    if invoice.account_id != account_id:
        raise ValueError("Invoice does not belong to the provided account")
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = (paid_at or datetime.now(UTC))
    await session.commit()
    await session.refresh(invoice, attribute_names=["items"])
    return invoice


async def mark_invoice_unpaid(
    session: AsyncSession,
    *,
    invoice: Invoice,
    account_id: uuid.UUID,
) -> Invoice:
    if invoice.account_id != account_id:
        raise ValueError("Invoice does not belong to the provided account")
    invoice.status = InvoiceStatus.PENDING
    invoice.paid_at = None
    await session.commit()
    await session.refresh(invoice, attribute_names=["items"])
    return invoice


async def process_payment(
    session: AsyncSession,
    *,
    invoice: Invoice,
    account_id: uuid.UUID,
    amount: Decimal,
) -> Invoice:
    if invoice.account_id != account_id:
        raise ValueError("Invoice does not belong to the provided account")
    if amount < invoice.total_amount:
        raise ValueError("Payment amount is less than total due")
    return await mark_invoice_paid(session, invoice=invoice, account_id=account_id, paid_at=datetime.now(UTC))


async def list_outstanding_invoices(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> list[Invoice]:
    return await list_invoices(session, account_id=account_id, status=InvoiceStatus.PENDING)


async def _recalculate_total(session: AsyncSession, invoice: Invoice) -> None:
    await session.flush()
    await session.refresh(invoice, attribute_names=["items"])
    total = sum((item.amount for item in invoice.items), start=Decimal("0"))
    invoice.total_amount = total
    session.add(invoice)
