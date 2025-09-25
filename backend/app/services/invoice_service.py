"""Invoice orchestration utilities."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Deposit,
    DepositStatus,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    OwnerProfile,
    Promotion,
    PromotionKind,
    Reservation,
)
from app.services import pricing_service

_CURRENCY_QUANT = Decimal("0.01")


class InvoiceNotFoundError(RuntimeError):
    """Raised when an invoice is not present."""


async def create_invoice_for_reservation(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> Invoice:
    reservation = await session.get(
        Reservation,
        reservation_id,
        options=[selectinload(Reservation.invoice).selectinload(Invoice.items)],
    )
    if reservation is None or reservation.account_id != account_id:
        raise ValueError("Reservation not found for account")
    if reservation.invoice is not None:
        raise ValueError("Invoice already exists for reservation")

    invoice = Invoice(
        account_id=account_id,
        reservation_id=reservation_id,
        status=InvoiceStatus.PENDING,
    )
    base_item = InvoiceItem(
        description="Reservation base rate", amount=reservation.base_rate
    )
    invoice.items.append(base_item)
    session.add(invoice)
    await session.flush()

    await compute_totals(session, account_id=account_id, invoice_id=invoice.id)
    return await _get_required_invoice(
        session, account_id=account_id, invoice_id=invoice.id
    )


async def compute_totals(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    invoice_id: uuid.UUID,
    promotion_code: str | None = None,
) -> Invoice:
    invoice = await _get_required_invoice(
        session, account_id=account_id, invoice_id=invoice_id
    )
    quote = await pricing_service.quote_reservation(
        session, reservation_id=invoice.reservation_id
    )
    invoice.subtotal = _quantize(quote.subtotal)
    invoice.discount_total = _quantize(quote.discount_total)
    invoice.tax_total = _quantize(quote.tax_total)

    promo_discount = Decimal("0")
    if promotion_code:
        promotion = await _get_active_promotion(
            session,
            account_id=account_id,
            code=promotion_code,
            as_of=invoice.reservation.start_at.date() if invoice.reservation else None,
        )
        promo_discount = _calculate_promotion_discount(promotion, invoice.subtotal)
        invoice.discount_total = _quantize(invoice.discount_total + promo_discount)

    invoice.total_amount = _quantize(
        invoice.subtotal - invoice.discount_total + invoice.tax_total
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(
        invoice,
        attribute_names=[
            "subtotal",
            "discount_total",
            "tax_total",
            "total_amount",
            "items",
        ],
    )
    return invoice


async def apply_promotion(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    invoice_id: uuid.UUID,
    code: str,
) -> Invoice:
    return await compute_totals(
        session, account_id=account_id, invoice_id=invoice_id, promotion_code=code
    )


async def hold_deposit(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
    owner_id: uuid.UUID,
    amount: Decimal,
) -> Deposit:
    reservation = await session.get(Reservation, reservation_id)
    if reservation is None or reservation.account_id != account_id:
        raise ValueError("Reservation not found for account")
    owner = await session.get(
        OwnerProfile,
        owner_id,
        options=[selectinload(OwnerProfile.user)],
    )
    if owner is None or owner.user is None or owner.user.account_id != account_id:
        raise ValueError("Owner not found for account")
    if amount <= 0:
        raise ValueError("Deposit amount must be positive")

    deposit = Deposit(
        account_id=account_id,
        reservation_id=reservation_id,
        owner_id=owner_id,
        amount=_quantize(amount),
        status=DepositStatus.HELD,
    )
    session.add(deposit)
    await session.commit()
    await session.refresh(deposit)
    return deposit


async def change_deposit_status(
    session: AsyncSession,
    *,
    deposit_id: uuid.UUID,
    account_id: uuid.UUID,
    status: DepositStatus,
) -> Deposit:
    deposit = await session.get(Deposit, deposit_id)
    if deposit is None or deposit.account_id != account_id:
        raise ValueError("Deposit not found for account")
    deposit.status = status
    await session.commit()
    await session.refresh(deposit)
    return deposit


async def consume_deposit(
    session: AsyncSession,
    *,
    deposit_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Deposit:
    return await change_deposit_status(
        session,
        deposit_id=deposit_id,
        account_id=account_id,
        status=DepositStatus.CONSUMED,
    )


async def refund_deposit(
    session: AsyncSession,
    *,
    deposit_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Deposit:
    return await change_deposit_status(
        session,
        deposit_id=deposit_id,
        account_id=account_id,
        status=DepositStatus.REFUNDED,
    )


async def forfeit_deposit(
    session: AsyncSession,
    *,
    deposit_id: uuid.UUID,
    account_id: uuid.UUID,
) -> Deposit:
    return await change_deposit_status(
        session,
        deposit_id=deposit_id,
        account_id=account_id,
        status=DepositStatus.FORFEITED,
    )


async def consume_reservation_deposits(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> list[Deposit]:
    stmt: Select[Deposit] = (
        select(Deposit)
        .where(
            Deposit.account_id == account_id,
            Deposit.reservation_id == reservation_id,
            Deposit.status == DepositStatus.HELD,
        )
        .order_by(Deposit.created_at.asc())
    )
    result = await session.execute(stmt)
    deposits = list(result.scalars())
    if not deposits:
        return []
    for deposit in deposits:
        deposit.status = DepositStatus.CONSUMED
    await session.commit()
    for deposit in deposits:
        await session.refresh(deposit)
    return deposits


async def _get_required_invoice(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Invoice:
    stmt: Select[Invoice] = (
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.account_id == account_id)
        .options(selectinload(Invoice.items), selectinload(Invoice.reservation))
    )
    result = await session.execute(stmt)
    invoice = result.scalars().unique().one_or_none()
    if invoice is None:
        raise InvoiceNotFoundError("Invoice not found")
    return invoice


async def _get_active_promotion(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    code: str,
    as_of: date | None,
) -> Promotion:
    stmt = select(Promotion).where(
        Promotion.account_id == account_id,
        Promotion.code == code,
        Promotion.active.is_(True),
    )
    result = await session.execute(stmt)
    promotion = result.scalars().one_or_none()
    if promotion is None:
        raise ValueError("Promotion code not found")

    as_of_date = as_of or datetime.now(UTC).date()
    if promotion.starts_on and promotion.starts_on > as_of_date:
        raise ValueError("Promotion is not active yet")
    if promotion.ends_on and promotion.ends_on < as_of_date:
        raise ValueError("Promotion has expired")
    return promotion


def _calculate_promotion_discount(promotion: Promotion, subtotal: Decimal) -> Decimal:
    if promotion.kind is PromotionKind.AMOUNT:
        return _quantize(min(subtotal, promotion.value))
    if promotion.value <= 0:
        return Decimal("0")
    percent = promotion.value / Decimal("100")
    return _quantize(subtotal * percent)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_CURRENCY_QUANT, rounding=ROUND_HALF_UP)
