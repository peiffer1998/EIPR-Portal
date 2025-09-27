"""Billing services for invoices."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Final

from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus
from app.models.owner_profile import OwnerProfile
from app.models.pet import Pet
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.invoice import InvoiceItemCreate
from app.services import invoice_service

_MONEY_PLACES: Final = Decimal("0.01")


def _to_money(value: Decimal | float | str) -> Decimal:
    """Normalize numbers to a fixed-point currency representation."""

    return Decimal(value).quantize(_MONEY_PLACES, rounding=ROUND_HALF_UP)


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
    stmt: Select[tuple[Invoice]] = select(Invoice).where(
        Invoice.account_id == account_id
    )
    if status is not None:
        stmt = stmt.where(Invoice.status == status)
    stmt = stmt.options(selectinload(Invoice.items)).order_by(Invoice.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def search_invoices(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    status: InvoiceStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Invoice], int]:
    """Return paginated invoices with optional filters applied."""

    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    owner_user = aliased(User)

    base_stmt: Select[tuple[Invoice]] = (
        select(Invoice)
        .outerjoin(Reservation, Invoice.reservation_id == Reservation.id)
        .outerjoin(Pet, Reservation.pet_id == Pet.id)
        .outerjoin(OwnerProfile, Pet.owner_id == OwnerProfile.id)
        .outerjoin(owner_user, OwnerProfile.user_id == owner_user.id)
        .where(Invoice.account_id == account_id)
    )

    if status is not None:
        base_stmt = base_stmt.where(Invoice.status == status)
    if date_from is not None:
        base_stmt = base_stmt.where(Invoice.created_at >= date_from)
    if date_to is not None:
        base_stmt = base_stmt.where(Invoice.created_at <= date_to)
    if query:
        pattern = f"%{query}%"
        base_stmt = base_stmt.where(
            or_(
                cast(Invoice.id, String).ilike(pattern),
                cast(Invoice.reservation_id, String).ilike(pattern),
                owner_user.first_name.ilike(pattern),
                owner_user.last_name.ilike(pattern),
                owner_user.email.ilike(pattern),
                owner_user.phone_number.ilike(pattern),
                Pet.name.ilike(pattern),
            )
        )

    count_stmt = base_stmt.with_only_columns(
        func.count(func.distinct(Invoice.id))
    ).order_by(None)
    total = (await session.execute(count_stmt)).scalar_one()

    results_stmt = (
        base_stmt.options(
            selectinload(Invoice.reservation)
            .selectinload(Reservation.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.user)
        )
        .order_by(Invoice.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(results_stmt)
    invoices = list(result.scalars().unique().all())
    return invoices, int(total)


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
    promotion_code: str | None = None,
) -> Invoice:
    reservation = await _ensure_reservation(
        session, account_id=account_id, reservation_id=reservation_id
    )
    if reservation.invoice is not None:
        raise ValueError("Invoice already exists for reservation")

    invoice_id = await invoice_service.create_from_reservation(
        session,
        reservation_id=reservation_id,
        account_id=account_id,
        promotion_code=promotion_code,
    )
    return await _get_required_invoice(
        session, account_id=account_id, invoice_id=invoice_id
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
        InvoiceItem(description=payload.description, amount=_to_money(payload.amount))
    )
    await _recalculate_totals(session, invoice)
    await session.commit()
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
    if amount < invoice.total:
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


async def _recalculate_totals(session: AsyncSession, invoice: Invoice) -> None:
    await session.flush()
    await session.refresh(invoice, attribute_names=["items"])

    positive = Decimal("0")
    discounts = Decimal("0")
    for item in invoice.items:
        amount = _to_money(item.amount)
        item.amount = amount
        if amount >= 0:
            positive += amount
        else:
            discounts += -amount

    invoice.subtotal = _to_money(positive)
    invoice.discount_total = _to_money(discounts)
    invoice.tax_total = _to_money(invoice.tax_total or Decimal("0"))
    invoice.total = _to_money(
        invoice.subtotal - invoice.discount_total + invoice.tax_total
    )
    credits_total = _to_money(invoice.credits_total or Decimal("0"))
    invoice.credits_total = credits_total
    remainder = invoice.total - credits_total
    invoice.total_amount = _to_money(
        remainder if remainder > Decimal("0") else Decimal("0")
    )
    session.add(invoice)
