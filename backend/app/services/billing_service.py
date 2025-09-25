"""Billing services for invoices."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.owner_profile import OwnerProfile
from app.models.pet import Pet
from app.models.reservation import Reservation
from app.schemas.invoice import InvoiceItemCreate
from app.services import invoice_service


async def list_invoices(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    status: InvoiceStatus | None = None,
) -> list[Invoice]:
    stmt: Select[tuple[Invoice]] = select(Invoice).where(
        Invoice.account_id == account_id
    )
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
        .options(
            selectinload(Invoice.items),
            selectinload(Invoice.reservation)
            .selectinload(Reservation.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.user),
            selectinload(Invoice.reservation).selectinload(Reservation.location),
        )
    )
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def _get_required_invoice(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Invoice:
    invoice = await get_invoice(session, account_id=account_id, invoice_id=invoice_id)
    if invoice is None:
        raise RuntimeError("Invoice was not persisted as expected")
    return invoice


async def generate_invoice_for_reservation(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> Invoice:
    return await invoice_service.create_invoice_for_reservation(
        session, account_id=account_id, reservation_id=reservation_id
    )


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
    await session.flush()
    await invoice_service.compute_totals(
        session, account_id=account_id, invoice_id=invoice.id
    )
    return await _get_required_invoice(
        session, account_id=account_id, invoice_id=invoice.id
    )


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
    invoice.paid_at = paid_at or datetime.now(UTC)
    await session.commit()
    return await _get_required_invoice(
        session, account_id=account_id, invoice_id=invoice.id
    )


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
    return await _get_required_invoice(
        session, account_id=account_id, invoice_id=invoice.id
    )


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
    paid_invoice = await mark_invoice_paid(
        session, invoice=invoice, account_id=account_id, paid_at=datetime.now(UTC)
    )
    return paid_invoice


async def list_outstanding_invoices(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
) -> list[Invoice]:
    return await list_invoices(
        session, account_id=account_id, status=InvoiceStatus.PENDING
    )
