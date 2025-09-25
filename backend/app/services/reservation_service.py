"""Reservation management service helpers."""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.location import Location
from app.models.location_capacity import LocationCapacityRule
from app.models.owner_profile import OwnerProfile
from app.models.pet import Pet
from app.models.reservation import Reservation, ReservationStatus, ReservationType
from app.models.user import User

_ALLOWED_STATUS_TRANSITIONS: dict[ReservationStatus, set[ReservationStatus]] = {
    ReservationStatus.REQUESTED: {ReservationStatus.CONFIRMED, ReservationStatus.CANCELED},
    ReservationStatus.CONFIRMED: {
        ReservationStatus.CHECKED_IN,
        ReservationStatus.CANCELED,
    },
    ReservationStatus.CHECKED_IN: {ReservationStatus.CHECKED_OUT},
    ReservationStatus.CHECKED_OUT: set(),
    ReservationStatus.CANCELED: set(),
}

_ACTIVE_RESERVATION_STATUSES = {
    ReservationStatus.REQUESTED,
    ReservationStatus.CONFIRMED,
    ReservationStatus.CHECKED_IN,
}


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _base_reservation_query(account_id: uuid.UUID):
    return (
        select(Reservation)
        .options(
            selectinload(Reservation.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.user),
            selectinload(Reservation.location),
        )
        .where(Reservation.account_id == account_id)
        .order_by(Reservation.start_at.desc())
    )


async def list_reservations(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> Sequence[Reservation]:
    stmt = _base_reservation_query(account_id).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def get_reservation(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> Reservation | None:
    stmt = _base_reservation_query(account_id).where(Reservation.id == reservation_id)
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def _validate_pet(
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
        raise ValueError("Pet does not belong to the provided account")
    return pet


async def _validate_location(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
) -> Location:
    location = await session.get(Location, location_id)
    if location is None or location.account_id != account_id:
        raise ValueError("Location does not belong to the provided account")
    return location


def _validate_times(start_at: datetime, end_at: datetime) -> None:
    if start_at >= end_at:
        raise ValueError("Reservation end time must be after start time")


async def create_reservation(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    pet_id: uuid.UUID,
    location_id: uuid.UUID,
    reservation_type: ReservationType,
    start_at: datetime,
    end_at: datetime,
    base_rate: Decimal,
    status: ReservationStatus = ReservationStatus.REQUESTED,
    notes: str | None = None,
) -> Reservation:
    _validate_times(start_at, end_at)
    await _validate_pet(session, account_id=account_id, pet_id=pet_id)
    await _validate_location(session, account_id=account_id, location_id=location_id)
    await _ensure_capacity_available(
        session,
        account_id=account_id,
        location_id=location_id,
        reservation_type=reservation_type,
        start_at=start_at,
        end_at=end_at,
        status=status,
    )

    reservation = Reservation(
        account_id=account_id,
        location_id=location_id,
        pet_id=pet_id,
        reservation_type=reservation_type,
        status=status,
        start_at=start_at,
        end_at=end_at,
        base_rate=base_rate,
        notes=notes,
    )
    session.add(reservation)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(reservation)
    return reservation


def _validate_status_transition(current: ReservationStatus, target: ReservationStatus) -> None:
    if target == current:
        return
    allowed = _ALLOWED_STATUS_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid status transition from {current} to {target}")


async def update_reservation(
    session: AsyncSession,
    *,
    reservation: Reservation,
    account_id: uuid.UUID,
    pet_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    reservation_type: ReservationType | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    base_rate: Decimal | None = None,
    status: ReservationStatus | None = None,
    notes: str | None = None,
) -> Reservation:
    if reservation.account_id != account_id:
        raise ValueError("Reservation does not belong to the provided account")

    if pet_id is not None and pet_id != reservation.pet_id:
        await _validate_pet(session, account_id=account_id, pet_id=pet_id)
        reservation.pet_id = pet_id

    if location_id is not None and location_id != reservation.location_id:
        await _validate_location(session, account_id=account_id, location_id=location_id)
        reservation.location_id = location_id

    if reservation_type is not None:
        reservation.reservation_type = reservation_type

    if start_at is not None:
        reservation.start_at = start_at
    if end_at is not None:
        reservation.end_at = end_at
    if start_at is not None or end_at is not None:
        _validate_times(reservation.start_at, reservation.end_at)

    if base_rate is not None:
        reservation.base_rate = base_rate

    if status is not None:
        _validate_status_transition(reservation.status, status)
        reservation.status = status

    if notes is not None:
        reservation.notes = notes

    await _ensure_capacity_available(
        session,
        account_id=account_id,
        location_id=reservation.location_id,
        reservation_type=reservation.reservation_type,
        start_at=reservation.start_at,
        end_at=reservation.end_at,
        status=reservation.status,
        exclude_reservation_id=reservation.id,
    )

    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)
    return reservation


async def delete_reservation(
    session: AsyncSession,
    *,
    reservation: Reservation,
    account_id: uuid.UUID,
) -> None:
    if reservation.account_id != account_id:
        raise ValueError("Reservation does not belong to the provided account")
    await session.delete(reservation)
    await session.commit()


async def _ensure_capacity_available(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    reservation_type: ReservationType,
    start_at: datetime,
    end_at: datetime,
    status: ReservationStatus,
    exclude_reservation_id: uuid.UUID | None = None,
) -> None:
    """Validate that a reservation falls within configured capacity limits."""
    if status not in _ACTIVE_RESERVATION_STATUSES:
        return

    result = await session.execute(
        select(LocationCapacityRule.max_active).where(
            LocationCapacityRule.location_id == location_id,
            LocationCapacityRule.reservation_type == reservation_type,
        )
    )
    max_active = result.scalar_one_or_none()
    if max_active is None:
        return

    overlap_stmt = select(func.count()).select_from(Reservation).where(
        Reservation.account_id == account_id,
        Reservation.location_id == location_id,
        Reservation.reservation_type == reservation_type,
        Reservation.status.in_(_ACTIVE_RESERVATION_STATUSES),
        Reservation.end_at > start_at,
        Reservation.start_at < end_at,
    )
    if exclude_reservation_id is not None:
        overlap_stmt = overlap_stmt.where(Reservation.id != exclude_reservation_id)

    count_active = (await session.execute(overlap_stmt)).scalar_one()
    if count_active >= max_active:
        raise ValueError("Capacity limit reached for the selected slot")


async def get_daily_availability(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    reservation_type: ReservationType,
    start_date: date,
    end_date: date,
) -> list[dict[str, object]]:
    """Return availability per day for the requested range."""
    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    await _validate_location(session, account_id=account_id, location_id=location_id)

    rule_result = await session.execute(
        select(LocationCapacityRule.max_active).where(
            LocationCapacityRule.location_id == location_id,
            LocationCapacityRule.reservation_type == reservation_type,
        )
    )
    max_active = rule_result.scalar_one_or_none()

    range_start = datetime.combine(start_date, time.min, tzinfo=UTC)
    range_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)

    reservations_result = await session.execute(
        select(Reservation.start_at, Reservation.end_at, Reservation.status)
        .where(
            Reservation.account_id == account_id,
            Reservation.location_id == location_id,
            Reservation.reservation_type == reservation_type,
            Reservation.status.in_(_ACTIVE_RESERVATION_STATUSES),
            Reservation.end_at > range_start,
            Reservation.start_at < range_end,
        )
    )
    reservations = [row for row in reservations_result.all()]

    days: list[dict[str, object]] = []
    current = start_date
    while current <= end_date:
        day_start = datetime.combine(current, time.min, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)
        bookings = 0
        for start_at, end_at, _ in reservations:
            start_dt = _coerce_utc(start_at)
            end_dt = _coerce_utc(end_at)
            if end_dt > day_start and start_dt < day_end:
                bookings += 1
        available = None
        if max_active is not None:
            available = max(max_active - bookings, 0)

        days.append(
            {
                "date": current,
                "capacity": max_active,
                "booked": bookings,
                "available": available,
            }
        )
        current += timedelta(days=1)

    return days
