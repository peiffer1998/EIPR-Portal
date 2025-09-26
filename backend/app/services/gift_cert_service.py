"""Gift certificate issuance and redemption services."""

from __future__ import annotations

import secrets
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Final
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    GiftCertificate,
    Invoice,
    InvoiceItem,
    Location,
    OwnerProfile,
    Pet,
    Reservation,
    ReservationStatus,
    ReservationType,
    StoreCreditLedger,
    StoreCreditSource,
)

_CURRENCY_UNIT: Final = Decimal("0.01")
_ROUNDING_MODE: Final = ROUND_HALF_UP


def _to_money(value: Decimal | float | str) -> Decimal:
    return Decimal(value).quantize(_CURRENCY_UNIT, rounding=_ROUNDING_MODE)


def _generate_code(length: int = 12) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def issue_gift_certificate(
    session: AsyncSession,
    *,
    account_id: UUID,
    purchaser_owner_id: UUID,
    amount: Decimal,
    recipient_owner_id: UUID | None = None,
    recipient_email: str | None = None,
    expires_on: date | None = None,
    code: str | None = None,
) -> GiftCertificate:
    """Create a new gift certificate record (without generating an invoice)."""

    normalized_amount = _to_money(amount)
    if normalized_amount <= Decimal("0"):
        raise ValueError("Gift certificate amount must be positive")

    purchaser = await _load_owner(session, purchaser_owner_id)
    if purchaser is None or purchaser.user is None:
        raise ValueError("Purchaser owner not found")
    if purchaser.user.account_id != account_id:
        raise ValueError("Purchaser owner does not belong to account")

    if recipient_owner_id is not None:
        recipient_owner = await _load_owner(session, recipient_owner_id)
        if recipient_owner is None or recipient_owner.user is None:
            raise ValueError("Recipient owner not found")
        if recipient_owner.user.account_id != account_id:
            raise ValueError("Recipient owner does not belong to account")

    certificate = GiftCertificate(
        account_id=account_id,
        code=code or _generate_code(),
        original_value=normalized_amount,
        remaining_value=normalized_amount,
        purchaser_owner_id=purchaser_owner_id,
        recipient_owner_id=recipient_owner_id,
        recipient_email=recipient_email,
        expires_on=expires_on,
        active=True,
    )
    session.add(certificate)
    await session.commit()
    await session.refresh(certificate)
    return certificate


async def purchase_gift_certificate(
    session: AsyncSession,
    *,
    account_id: UUID,
    purchaser_owner_id: UUID,
    amount: Decimal,
    recipient_owner_id: UUID | None = None,
    recipient_email: str | None = None,
    expires_on: date | None = None,
) -> tuple[UUID, GiftCertificate]:
    """Create an invoice and gift certificate for a purchase."""

    normalized_amount = _to_money(amount)
    if normalized_amount <= Decimal("0"):
        raise ValueError("Gift certificate amount must be positive")

    purchaser = await _load_owner(session, purchaser_owner_id)
    if purchaser is None or purchaser.user is None:
        raise ValueError("Purchaser owner not found")
    if purchaser.user.account_id != account_id:
        raise ValueError("Purchaser owner does not belong to account")

    if recipient_owner_id is not None:
        recipient_owner = await _load_owner(session, recipient_owner_id)
        if recipient_owner is None or recipient_owner.user is None:
            raise ValueError("Recipient owner not found")
        if recipient_owner.user.account_id != account_id:
            raise ValueError("Recipient owner does not belong to account")

    pet = await _fetch_primary_pet(session, purchaser_owner_id)
    if pet is None:
        raise ValueError("Owner must have a pet on file to purchase gift certificates")

    location = await _fetch_default_location(session, account_id)
    if location is None:
        raise ValueError("Account is missing a location for store purchases")

    now = datetime.now(UTC)
    reservation = Reservation(
        account_id=account_id,
        location_id=location.id,
        pet_id=pet.id,
        reservation_type=ReservationType.OTHER,
        status=ReservationStatus.CONFIRMED,
        start_at=now,
        end_at=now,
        base_rate=Decimal("0.00"),
        notes="Gift certificate purchase",
    )
    session.add(reservation)
    await session.flush()

    invoice = Invoice(
        account_id=account_id,
        reservation_id=reservation.id,
        subtotal=normalized_amount,
        discount_total=Decimal("0.00"),
        tax_total=Decimal("0.00"),
        credits_total=Decimal("0.00"),
        total=normalized_amount,
        total_amount=normalized_amount,
    )
    session.add(invoice)
    await session.flush()

    session.add(
        InvoiceItem(
            invoice_id=invoice.id,
            description="Gift certificate",
            amount=normalized_amount,
        )
    )

    certificate = GiftCertificate(
        account_id=account_id,
        code=_generate_code(),
        original_value=normalized_amount,
        remaining_value=normalized_amount,
        purchaser_owner_id=purchaser_owner_id,
        recipient_owner_id=recipient_owner_id,
        recipient_email=recipient_email,
        expires_on=expires_on,
        active=True,
    )
    session.add(certificate)

    await session.commit()
    await session.refresh(invoice)
    await session.refresh(certificate)
    return invoice.id, certificate


async def redeem_gift_certificate(
    session: AsyncSession,
    *,
    code: str,
    account_id: UUID,
    owner_id: UUID,
) -> Decimal:
    """Redeem a gift certificate into store credit for the provided owner."""

    owner = await _load_owner(session, owner_id)
    if owner is None or owner.user is None:
        raise ValueError("Owner not found")
    if owner.user.account_id != account_id:
        raise ValueError("Owner does not belong to account")

    certificate = await _load_certificate(session, code, account_id)
    if certificate is None or not certificate.active:
        raise ValueError("Gift certificate is not active")

    remaining = _to_money(certificate.remaining_value)
    if remaining <= Decimal("0"):
        raise ValueError("Gift certificate has no remaining value")

    certificate.remaining_value = Decimal("0.00")
    certificate.active = False
    certificate.recipient_owner_id = owner_id

    ledger_entry = StoreCreditLedger(
        account_id=account_id,
        owner_id=owner_id,
        amount=remaining,
        source=StoreCreditSource.REDEEM_GC,
        note=f"Redeemed gift certificate {certificate.code}",
    )
    session.add(ledger_entry)

    await session.commit()
    return remaining


async def _load_owner(session: AsyncSession, owner_id: UUID) -> OwnerProfile | None:
    stmt = (
        select(OwnerProfile)
        .where(OwnerProfile.id == owner_id)
        .options(selectinload(OwnerProfile.user))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_certificate(
    session: AsyncSession, code: str, account_id: UUID
) -> GiftCertificate | None:
    stmt = select(GiftCertificate).where(
        GiftCertificate.code == code,
        GiftCertificate.account_id == account_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _fetch_primary_pet(session: AsyncSession, owner_id: UUID) -> Pet | None:
    stmt = (
        select(Pet)
        .where(Pet.owner_id == owner_id)
        .order_by(Pet.created_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _fetch_default_location(
    session: AsyncSession, account_id: UUID
) -> Location | None:
    stmt = (
        select(Location)
        .where(Location.account_id == account_id)
        .order_by(Location.created_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
