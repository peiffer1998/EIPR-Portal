"""Booking and lifecycle management for grooming appointments."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Final, Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CommissionType,
    GroomingAddon,
    GroomingAppointment,
    GroomingAppointmentStatus,
    GroomingService,
    Invoice,
    InvoiceItem,
    OwnerProfile,
    Pet,
    Reservation,
    Specialist,
)

_MONEY_PLACES: Final = Decimal("0.01")

_BLOCKING_STATUSES: set[GroomingAppointmentStatus] = {
    GroomingAppointmentStatus.REQUESTED,
    GroomingAppointmentStatus.SCHEDULED,
    GroomingAppointmentStatus.CHECKED_IN,
    GroomingAppointmentStatus.IN_PROGRESS,
    GroomingAppointmentStatus.COMPLETED,
}

_ALLOWED_STATUS_TRANSITIONS: dict[
    GroomingAppointmentStatus, set[GroomingAppointmentStatus]
] = {
    GroomingAppointmentStatus.REQUESTED: {
        GroomingAppointmentStatus.SCHEDULED,
        GroomingAppointmentStatus.CANCELED,
    },
    GroomingAppointmentStatus.SCHEDULED: {
        GroomingAppointmentStatus.CHECKED_IN,
        GroomingAppointmentStatus.IN_PROGRESS,
        GroomingAppointmentStatus.CANCELED,
        GroomingAppointmentStatus.NO_SHOW,
    },
    GroomingAppointmentStatus.CHECKED_IN: {
        GroomingAppointmentStatus.IN_PROGRESS,
        GroomingAppointmentStatus.CANCELED,
    },
    GroomingAppointmentStatus.IN_PROGRESS: {
        GroomingAppointmentStatus.COMPLETED,
        GroomingAppointmentStatus.CANCELED,
    },
    GroomingAppointmentStatus.COMPLETED: set(),
    GroomingAppointmentStatus.CANCELED: set(),
    GroomingAppointmentStatus.NO_SHOW: set(),
}


def _to_money(value: Decimal | float | str) -> Decimal:
    return Decimal(value).quantize(_MONEY_PLACES, rounding=ROUND_HALF_UP)


def _normalize_datetime(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


async def _get_owner(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> OwnerProfile:
    owner = await session.get(
        OwnerProfile,
        owner_id,
        options=[selectinload(OwnerProfile.user)],
    )
    if owner is None or owner.user.account_id != account_id:
        raise ValueError("Owner not found for account")
    return owner


async def _get_pet(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    pet_id: uuid.UUID,
) -> Pet:
    pet = await session.get(
        Pet,
        pet_id,
        options=[selectinload(Pet.owner).selectinload(OwnerProfile.user)],
    )
    if pet is None or pet.owner.user.account_id != account_id:
        raise ValueError("Pet not found for account")
    return pet


async def _get_specialist(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    specialist_id: uuid.UUID,
) -> Specialist:
    specialist = await session.get(Specialist, specialist_id)
    if (
        specialist is None
        or specialist.account_id != account_id
        or not specialist.active
    ):
        raise ValueError("Specialist not available")
    return specialist


async def _get_service(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    service_id: uuid.UUID,
) -> GroomingService:
    service = await session.get(GroomingService, service_id)
    if service is None or service.account_id != account_id or not service.active:
        raise ValueError("Service not available")
    return service


async def _get_addons(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    addon_ids: Sequence[uuid.UUID],
) -> list[GroomingAddon]:
    if not addon_ids:
        return []
    stmt: Select[tuple[GroomingAddon]] = select(GroomingAddon).where(
        GroomingAddon.account_id == account_id,
        GroomingAddon.id.in_(addon_ids),
        GroomingAddon.active.is_(True),
    )
    result = await session.execute(stmt)
    addons = result.scalars().all()
    if len(addons) != len(set(addon_ids)):
        raise ValueError("Add-on not available")
    return list(addons)


async def _ensure_invoice(
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

    invoice = reservation.invoice
    if invoice is None:
        invoice = Invoice(
            account_id=account_id,
            reservation_id=reservation_id,
            subtotal=Decimal("0"),
            discount_total=Decimal("0"),
            tax_total=Decimal("0"),
            total=Decimal("0"),
            total_amount=Decimal("0"),
        )
        session.add(invoice)
        await session.flush()
        await session.refresh(invoice, attribute_names=["items"])
    return invoice


def _add_invoice_item(invoice: Invoice, *, description: str, amount: Decimal) -> None:
    normalized = _to_money(amount)
    invoice.items.append(InvoiceItem(description=description, amount=normalized))


def _recalculate_invoice_totals(invoice: Invoice) -> None:
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
    invoice.total = _to_money(
        invoice.subtotal - invoice.discount_total + invoice.tax_total
    )
    invoice.total_amount = invoice.total


async def _ensure_no_overlap(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    specialist_id: uuid.UUID,
    start_at: datetime,
    end_at: datetime,
    exclude_appointment_id: uuid.UUID | None = None,
) -> None:
    stmt = select(GroomingAppointment.id).where(
        GroomingAppointment.account_id == account_id,
        GroomingAppointment.specialist_id == specialist_id,
        GroomingAppointment.status.in_(_BLOCKING_STATUSES),
        GroomingAppointment.end_at > start_at,
        GroomingAppointment.start_at < end_at,
    )
    if exclude_appointment_id is not None:
        stmt = stmt.where(GroomingAppointment.id != exclude_appointment_id)
    result = await session.execute(stmt)
    if result.first() is not None:
        raise ValueError("Specialist already booked for that time range")


async def _get_appointment(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    appointment_id: uuid.UUID,
) -> GroomingAppointment:
    appointment = await session.get(
        GroomingAppointment,
        appointment_id,
        options=[
            selectinload(GroomingAppointment.addons),
            selectinload(GroomingAppointment.service),
            selectinload(GroomingAppointment.specialist),
        ],
    )
    if appointment is None or appointment.account_id != account_id:
        raise ValueError("Appointment not found for account")
    return appointment


async def book_appointment(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
    pet_id: uuid.UUID,
    specialist_id: uuid.UUID,
    service_id: uuid.UUID,
    addon_ids: Sequence[uuid.UUID] | None,
    start_at: datetime,
    notes: str | None = None,
    reservation_id: uuid.UUID | None = None,
) -> GroomingAppointment:
    owner = await _get_owner(session, account_id=account_id, owner_id=owner_id)
    pet = await _get_pet(session, account_id=account_id, pet_id=pet_id)
    if pet.owner_id != owner.id:
        raise ValueError("Pet does not belong to the specified owner")

    specialist = await _get_specialist(
        session, account_id=account_id, specialist_id=specialist_id
    )
    service = await _get_service(session, account_id=account_id, service_id=service_id)
    addons = await _get_addons(
        session,
        account_id=account_id,
        addon_ids=addon_ids or [],
    )

    start_at_utc = _normalize_datetime(start_at)
    total_minutes = service.base_duration_minutes + sum(
        addon.add_duration_minutes for addon in addons
    )
    if total_minutes <= 0:
        raise ValueError("Total duration must be positive")
    end_at = start_at_utc + timedelta(minutes=total_minutes)

    await _ensure_no_overlap(
        session,
        account_id=account_id,
        specialist_id=specialist_id,
        start_at=start_at_utc,
        end_at=end_at,
    )

    price_snapshot = service.base_price + sum(addon.add_price for addon in addons)
    commission_type = specialist.commission_type
    commission_rate = specialist.commission_rate
    commission_amount = compute_commission_amount(
        price_snapshot,
        commission_type,
        commission_rate,
    )

    appointment = GroomingAppointment(
        account_id=account_id,
        owner_id=owner.id,
        pet_id=pet.id,
        specialist_id=specialist.id,
        service_id=service.id,
        start_at=start_at_utc,
        end_at=end_at,
        status=GroomingAppointmentStatus.SCHEDULED,
        notes=notes,
        price_snapshot=_to_money(price_snapshot),
        commission_type=commission_type,
        commission_rate=(
            _to_money(commission_rate) if commission_rate is not None else None
        ),
        commission_amount=commission_amount,
        reservation_id=reservation_id,
    )
    appointment.addons.extend(addons)
    session.add(appointment)

    invoice: Invoice | None = None
    if reservation_id is not None:
        invoice = await _ensure_invoice(
            session, account_id=account_id, reservation_id=reservation_id
        )
        _add_invoice_item(
            invoice,
            description=f"Grooming - {service.name}",
            amount=service.base_price,
        )
        for addon in addons:
            _add_invoice_item(
                invoice,
                description=f"Add-on - {addon.name}",
                amount=addon.add_price,
            )
        _recalculate_invoice_totals(invoice)
        appointment.invoice_id = invoice.id

    await session.commit()
    await session.refresh(
        appointment,
        attribute_names=["addons", "service", "specialist", "invoice"],
    )
    if invoice is not None:
        await session.refresh(invoice, attribute_names=["items"])
    return appointment


async def reschedule_appointment(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    appointment_id: uuid.UUID,
    new_start_at: datetime,
) -> GroomingAppointment:
    appointment = await _get_appointment(
        session, account_id=account_id, appointment_id=appointment_id
    )
    duration = appointment.end_at - appointment.start_at
    new_start = _normalize_datetime(new_start_at)
    new_end = new_start + duration

    await _ensure_no_overlap(
        session,
        account_id=account_id,
        specialist_id=appointment.specialist_id,
        start_at=new_start,
        end_at=new_end,
        exclude_appointment_id=appointment.id,
    )

    appointment.start_at = new_start
    appointment.end_at = new_end
    await session.commit()
    await session.refresh(
        appointment,
        attribute_names=["addons", "service", "specialist"],
    )
    return appointment


async def cancel_appointment(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    appointment_id: uuid.UUID,
    reason: str | None = None,
) -> GroomingAppointment:
    appointment = await _get_appointment(
        session, account_id=account_id, appointment_id=appointment_id
    )
    appointment.status = GroomingAppointmentStatus.CANCELED
    if reason:
        note = appointment.notes or ""
        separator = "\n" if note else ""
        appointment.notes = f"{note}{separator}Canceled: {reason}"
    await session.commit()
    await session.refresh(
        appointment,
        attribute_names=["addons", "service", "specialist"],
    )
    return appointment


async def update_status(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    appointment_id: uuid.UUID,
    new_status: GroomingAppointmentStatus,
) -> GroomingAppointment:
    appointment = await _get_appointment(
        session, account_id=account_id, appointment_id=appointment_id
    )
    allowed = _ALLOWED_STATUS_TRANSITIONS[appointment.status]
    if new_status not in allowed:
        raise ValueError("Status transition not allowed")
    appointment.status = new_status
    await session.commit()
    await session.refresh(
        appointment,
        attribute_names=["addons", "service", "specialist"],
    )
    return appointment


def compute_commission_amount(
    price_snapshot: Decimal,
    commission_type: CommissionType | None,
    commission_rate: Decimal | None,
) -> Decimal | None:
    if commission_type is None or commission_rate is None:
        return None
    if commission_type is CommissionType.AMOUNT:
        return _to_money(commission_rate)
    # percent
    return _to_money(price_snapshot * (commission_rate / Decimal("100")))
