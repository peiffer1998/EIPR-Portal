"""Reservation management service helpers."""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.location import Location
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
