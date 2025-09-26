"""Package purchase and credit application services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Final
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CreditApplication,
    CreditApplicationType,
    Invoice,
    InvoiceItem,
    Location,
    OwnerProfile,
    PackageApplicationType,
    PackageCredit,
    PackageCreditSource,
    PackageType,
    Pet,
    Reservation,
    ReservationStatus,
    ReservationType,
)

_CURRENCY_UNIT: Final = Decimal("0.01")
_ROUNDING_MODE: Final = ROUND_HALF_UP


@dataclass(slots=True)
class PackageCreditApplication:
    """Summary of package credits applied to an invoice."""

    invoice_id: UUID
    applied_amount: Decimal = Decimal("0.00")
    units_consumed: dict[UUID, int] = field(default_factory=dict)


def _to_money(value: Decimal | float | str) -> Decimal:
    return Decimal(value).quantize(_CURRENCY_UNIT, rounding=_ROUNDING_MODE)


async def purchase_package(
    session: AsyncSession,
    *,
    owner_id: UUID,
    package_type_id: UUID,
    quantity: int = 1,
) -> UUID:
    """Create an invoice for a package purchase and ledger the credits."""

    if quantity <= 0:
        raise ValueError("Quantity must be positive")

    owner = await _load_owner(session, owner_id)
    if owner is None or owner.user is None:
        raise ValueError("Owner not found")

    package = await _load_package_type(session, package_type_id)
    if package is None or not package.active:
        raise ValueError("Package type not available")

    account_id = owner.user.account_id
    if package.account_id != account_id:
        raise ValueError("Package type not available for this account")

    pet = await _fetch_primary_pet(session, owner_id)
    if pet is None:
        raise ValueError("Owner must have a pet on file to purchase packages")

    location = await _fetch_default_location(session, account_id)
    if location is None:
        raise ValueError("Account is missing a location for store purchases")

    total_price = _to_money((package.price or Decimal("0")) * quantity)
    credits_purchased = package.credits_per_package * quantity

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
        notes="Store package purchase",
    )
    session.add(reservation)
    await session.flush()

    invoice = Invoice(
        account_id=account_id,
        reservation_id=reservation.id,
        subtotal=total_price,
        discount_total=Decimal("0.00"),
        tax_total=Decimal("0.00"),
        credits_total=Decimal("0.00"),
        total=total_price,
        total_amount=total_price,
    )
    session.add(invoice)
    await session.flush()

    session.add(
        InvoiceItem(
            invoice_id=invoice.id,
            description=f"{package.name} x{quantity}",
            amount=total_price,
        )
    )

    session.add(
        PackageCredit(
            account_id=account_id,
            owner_id=owner_id,
            package_type_id=package.id,
            credits=credits_purchased,
            source=PackageCreditSource.PURCHASE,
            invoice_id=invoice.id,
        )
    )

    await session.commit()
    await session.refresh(invoice)
    return invoice.id


async def apply_package_credits(
    session: AsyncSession,
    *,
    invoice_id: UUID,
    account_id: UUID,
) -> PackageCreditApplication:
    """Consume applicable package credits against an invoice."""

    invoice = await _load_invoice_for_application(session, invoice_id, account_id)
    if invoice is None:
        raise ValueError("Invoice not found")

    reservation = invoice.reservation
    if reservation is None or reservation.pet is None or reservation.pet.owner is None:
        raise ValueError("Invoice reservation is missing owner information")

    owner = reservation.pet.owner
    owner_id = owner.id
    summary = PackageCreditApplication(invoice_id=invoice.id)

    balance = _invoice_balance(invoice)
    if balance <= Decimal("0"):
        return summary

    packages = await _load_available_packages(session, owner_id, account_id)
    if not packages:
        return summary

    reservation_type = reservation.reservation_type

    for package_type, credits_available in packages:
        if credits_available <= 0:
            continue
        if not _package_applies_to_reservation(
            package_type.applies_to, reservation_type
        ):
            continue

        unit_value = _package_unit_value(package_type)
        if unit_value <= Decimal("0"):
            continue

        max_units_from_balance = int(
            (balance / unit_value).to_integral_value(rounding="ROUND_FLOOR")
        )
        if max_units_from_balance <= 0:
            continue

        units_to_consume = min(credits_available, max_units_from_balance)
        if units_to_consume <= 0:
            continue

        apply_amount = _to_money(unit_value * units_to_consume)
        if apply_amount <= Decimal("0"):
            continue

        session.add(
            PackageCredit(
                account_id=account_id,
                owner_id=owner_id,
                package_type_id=package_type.id,
                credits=-units_to_consume,
                source=PackageCreditSource.CONSUME,
                invoice_id=invoice.id,
                reservation_id=invoice.reservation_id,
            )
        )

        session.add(
            CreditApplication(
                account_id=account_id,
                invoice_id=invoice.id,
                type=CreditApplicationType.PACKAGE,
                reference_id=package_type.id,
                units=units_to_consume,
                amount=apply_amount,
            )
        )

        invoice.credits_total = _to_money(
            (invoice.credits_total or Decimal("0")) + apply_amount
        )
        invoice.total_amount = _remaining_total(invoice.total, invoice.credits_total)

        balance -= apply_amount
        summary.applied_amount += apply_amount
        summary.units_consumed[package_type.id] = (
            summary.units_consumed.get(package_type.id, 0) + units_to_consume
        )

        if balance <= Decimal("0"):
            break

    await session.commit()
    await session.refresh(invoice, attribute_names=["credits_total", "total_amount"])
    return summary


async def remaining_credits(
    session: AsyncSession,
    *,
    owner_id: UUID,
    account_id: UUID,
) -> list[dict[str, object]]:
    """Return remaining package credits grouped by package type."""

    packages = await _load_available_packages(session, owner_id, account_id)
    response: list[dict[str, object]] = []
    for package_type, credits_available in packages:
        if credits_available <= 0:
            continue
        response.append(
            {
                "package_type_id": package_type.id,
                "name": package_type.name,
                "applies_to": package_type.applies_to.value,
                "remaining": credits_available,
            }
        )
    return response


def _package_applies_to_reservation(
    applies_to: PackageApplicationType,
    reservation_type: ReservationType,
) -> bool:
    if applies_to is PackageApplicationType.CURRENCY:
        return True
    mapping = {
        PackageApplicationType.BOARDING: ReservationType.BOARDING,
        PackageApplicationType.DAYCARE: ReservationType.DAYCARE,
        PackageApplicationType.GROOMING: ReservationType.GROOMING,
    }
    expected = mapping.get(applies_to)
    return expected is None or reservation_type == expected


def _package_unit_value(package_type: PackageType) -> Decimal:
    if not package_type.credits_per_package:
        return Decimal("0")
    price = package_type.price or Decimal("0")
    if price <= Decimal("0"):
        return Decimal("0")
    return _to_money(price / Decimal(package_type.credits_per_package))


def _invoice_balance(invoice: Invoice) -> Decimal:
    total = _to_money(invoice.total or Decimal("0"))
    credits = _to_money(invoice.credits_total or Decimal("0"))
    balance = total - credits
    return balance if balance > Decimal("0") else Decimal("0.00")


def _remaining_total(total: Decimal | None, credits: Decimal | None) -> Decimal:
    total_value = _to_money(total or Decimal("0"))
    credit_value = _to_money(credits or Decimal("0"))
    remainder = total_value - credit_value
    return remainder if remainder > Decimal("0") else Decimal("0.00")


async def _load_owner(session: AsyncSession, owner_id: UUID) -> OwnerProfile | None:
    stmt: Select[OwnerProfile] = (
        select(OwnerProfile)
        .options(selectinload(OwnerProfile.user))
        .where(OwnerProfile.id == owner_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_package_type(
    session: AsyncSession, package_type_id: UUID
) -> PackageType | None:
    result = await session.execute(
        select(PackageType).where(PackageType.id == package_type_id)
    )
    return result.scalar_one_or_none()


async def _fetch_primary_pet(session: AsyncSession, owner_id: UUID) -> Pet | None:
    stmt: Select[Pet] = (
        select(Pet)
        .where(Pet.owner_id == owner_id)
        .order_by(Pet.created_at.asc())
        .limit(1)
        .options(selectinload(Pet.owner))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _fetch_default_location(
    session: AsyncSession, account_id: UUID
) -> Location | None:
    stmt: Select[Location] = (
        select(Location)
        .where(Location.account_id == account_id)
        .order_by(Location.created_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_invoice_for_application(
    session: AsyncSession, invoice_id: UUID, account_id: UUID
) -> Invoice | None:
    stmt: Select[Invoice] = (
        select(Invoice)
        .options(
            selectinload(Invoice.reservation)
            .selectinload(Reservation.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.user),
            selectinload(Invoice.items),
            selectinload(Invoice.credit_applications),
        )
        .where(Invoice.id == invoice_id, Invoice.account_id == account_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _load_available_packages(
    session: AsyncSession, owner_id: UUID, account_id: UUID
) -> list[tuple[PackageType, int]]:
    stmt = (
        select(
            PackageType,
            func.coalesce(func.sum(PackageCredit.credits), 0).label("credits"),
        )
        .join(PackageCredit, PackageCredit.package_type_id == PackageType.id)
        .where(
            PackageCredit.owner_id == owner_id,
            PackageCredit.account_id == account_id,
        )
        .group_by(PackageType.id)
        .options(selectinload(PackageType.account))
    )
    result = await session.execute(stmt)
    packages: list[tuple[PackageType, int]] = []
    for package_type, credits in result.all():
        packages.append((package_type, int(credits)))
    return packages
