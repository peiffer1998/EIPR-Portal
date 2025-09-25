"""Aggregated views for daily feeding schedules."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    FeedingSchedule,
    Location,
    OwnerProfile,
    Pet,
    Reservation,
    ReservationType,
    User,
)
from app.schemas.ops_p5 import FeedingBoardItem, FeedingBoardRow


def _resolve_timezone(location: Location) -> ZoneInfo:
    """Return the location timezone or UTC when unknown."""
    try:
        return ZoneInfo(location.timezone)
    except ZoneInfoNotFoundError:  # pragma: no cover - depends on system tz database
        return ZoneInfo("UTC")


def _day_bounds(target_date: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """Return UTC-aware start/end bounds for the given local date."""
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
    service: ReservationType | None,
    start_utc: datetime,
    end_utc: datetime,
) -> list[FeedingBoardRow]:
    filters = [
        Reservation.account_id == account_id,
        Reservation.location_id == location_id,
        FeedingSchedule.scheduled_at >= start_utc,
        FeedingSchedule.scheduled_at < end_utc,
    ]
    if service is not None:
        filters.append(Reservation.reservation_type == service)

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
            FeedingSchedule.scheduled_at,
            FeedingSchedule.food,
            FeedingSchedule.quantity,
            FeedingSchedule.notes,
        )
        .join(Reservation, FeedingSchedule.reservation_id == Reservation.id)
        .join(Pet, Reservation.pet_id == Pet.id)
        .join(OwnerProfile, Pet.owner_id == OwnerProfile.id)
        .join(User, OwnerProfile.user_id == User.id)
        .where(and_(*filters))
        .order_by(
            User.last_name.asc(), Pet.name.asc(), FeedingSchedule.scheduled_at.asc()
        )
    )
    result = await session.execute(stmt)
    rows = result.all()

    grouped: dict[uuid.UUID, FeedingBoardRow] = {}
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
        food,
        quantity,
        feeding_notes,
    ) in rows:
        item = FeedingBoardItem(
            scheduled_at=scheduled_at,
            food=food,
            quantity=quantity,
            notes=feeding_notes,
        )
        if reservation_id not in grouped:
            owner_name = f"{owner_first} {owner_last}".strip()
            grouped[reservation_id] = FeedingBoardRow(
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
    service: ReservationType | None = None,
) -> list[FeedingBoardRow]:
    """Return feeding board rows for the supplied date."""
    location = await _get_location(
        session, account_id=account_id, location_id=location_id
    )
    tz = _resolve_timezone(location)
    start_utc, end_utc = _day_bounds(target_date, tz)
    return await _list_for_bounds(
        session,
        account_id=account_id,
        location_id=location_id,
        service=service,
        start_utc=start_utc,
        end_utc=end_utc,
    )


async def list_today(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    service: ReservationType,
) -> list[FeedingBoardRow]:
    """Return feeding board rows for the current local day."""
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
        service=service,
        start_utc=start_utc,
        end_utc=end_utc,
    )
