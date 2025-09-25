"""Aggregated views for daily medication schedules."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Location,
    MedicationSchedule,
    OwnerProfile,
    Pet,
    Reservation,
    User,
)
from app.schemas.ops_p5 import MedicationBoardItem, MedicationBoardRow


def _resolve_timezone(location: Location) -> ZoneInfo:
    try:
        return ZoneInfo(location.timezone)
    except ZoneInfoNotFoundError:  # pragma: no cover - depends on system tz database
        return ZoneInfo("UTC")


def _day_bounds(target_date: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    local_start = datetime.combine(target_date, time.min, tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


async def _get_location(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
) -> Location:
    location = await session.get(Location, location_id)
    if location is None or location.account_id != account_id:
        raise ValueError("Location not found for this account")
    return location


async def _list_for_bounds(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    start_utc: datetime,
    end_utc: datetime,
) -> list[MedicationBoardRow]:
    stmt: Select = (
        select(
            Reservation.id,
            Reservation.reservation_type,
            Reservation.start_at,
            Reservation.end_at,
            Reservation.notes,
            Pet.name,
            User.first_name,
            User.last_name,
            MedicationSchedule.scheduled_at,
            MedicationSchedule.medication,
            MedicationSchedule.dosage,
            MedicationSchedule.notes,
        )
        .join(Reservation, MedicationSchedule.reservation_id == Reservation.id)
        .join(Pet, Reservation.pet_id == Pet.id)
        .join(OwnerProfile, Pet.owner_id == OwnerProfile.id)
        .join(User, OwnerProfile.user_id == User.id)
        .where(
            and_(
                Reservation.account_id == account_id,
                Reservation.location_id == location_id,
                MedicationSchedule.scheduled_at >= start_utc,
                MedicationSchedule.scheduled_at < end_utc,
            )
        )
        .order_by(
            User.last_name.asc(), Pet.name.asc(), MedicationSchedule.scheduled_at.asc()
        )
    )

    result = await session.execute(stmt)
    rows = result.all()

    grouped: dict[uuid.UUID, MedicationBoardRow] = {}
    for (
        reservation_id,
        reservation_type,
        start_at,
        end_at,
        reservation_notes,
        pet_name,
        owner_first,
        owner_last,
        scheduled_at,
        medication,
        dosage,
        med_notes,
    ) in rows:
        item = MedicationBoardItem(
            scheduled_at=scheduled_at,
            medication=medication,
            dosage=dosage,
            notes=med_notes,
        )
        if reservation_id not in grouped:
            owner_name = f"{owner_first} {owner_last}".strip()
            grouped[reservation_id] = MedicationBoardRow(
                reservation_id=reservation_id,
                pet_name=pet_name,
                owner_name=owner_name,
                reservation_type=reservation_type,
                start_at=start_at,
                end_at=end_at,
                reservation_notes=reservation_notes,
                schedule_items=[item],
            )
        else:
            grouped[reservation_id].schedule_items.append(item)

    return list(grouped.values())


async def list_for_date(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    target_date: date,
) -> list[MedicationBoardRow]:
    location = await _get_location(
        session, account_id=account_id, location_id=location_id
    )
    tz = _resolve_timezone(location)
    start_utc, end_utc = _day_bounds(target_date, tz)
    return await _list_for_bounds(
        session,
        account_id=account_id,
        location_id=location_id,
        start_utc=start_utc,
        end_utc=end_utc,
    )


async def list_today(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
) -> list[MedicationBoardRow]:
    location = await _get_location(
        session, account_id=account_id, location_id=location_id
    )
    tz = _resolve_timezone(location)
    today_local = datetime.now(tz).date()
    start_utc, end_utc = _day_bounds(today_local, tz)
    return await _list_for_bounds(
        session,
        account_id=account_id,
        location_id=location_id,
        start_utc=start_utc,
        end_utc=end_utc,
    )
