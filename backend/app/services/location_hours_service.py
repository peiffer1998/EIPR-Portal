"""Manage location hours and closures."""
from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.location_hours import LocationClosure, LocationHour
from app.schemas.location_hours import (
    LocationClosureCreate,
    LocationClosureRead,
    LocationHourCreate,
    LocationHourUpdate,
)


async def _ensure_location(session: AsyncSession, *, account_id: uuid.UUID, location_id: uuid.UUID) -> Location:
    location = await session.get(Location, location_id)
    if location is None or location.account_id != account_id:
        raise ValueError("Location not found")
    return location


async def list_hours(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
) -> list[LocationHour]:
    await _ensure_location(session, account_id=account_id, location_id=location_id)
    stmt: Select[tuple[LocationHour]] = (
        select(LocationHour)
        .where(LocationHour.location_id == location_id)
        .order_by(LocationHour.day_of_week.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def upsert_hour(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    payload: LocationHourCreate,
) -> LocationHour:
    await _ensure_location(session, account_id=account_id, location_id=location_id)
    existing_stmt = select(LocationHour).where(
        LocationHour.location_id == location_id,
        LocationHour.day_of_week == payload.day_of_week,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is None:
        hour = LocationHour(
            location_id=location_id,
            day_of_week=payload.day_of_week,
            open_time=payload.open_time,
            close_time=payload.close_time,
            is_closed=payload.is_closed,
        )
        session.add(hour)
        await session.commit()
        await session.refresh(hour)
        return hour

    existing.open_time = payload.open_time
    existing.close_time = payload.close_time
    existing.is_closed = payload.is_closed
    await session.commit()
    await session.refresh(existing)
    return existing


async def update_hour(
    session: AsyncSession,
    *,
    hour: LocationHour,
    payload: LocationHourUpdate,
) -> LocationHour:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(hour, key, value)
    await session.commit()
    await session.refresh(hour)
    return hour


async def delete_hour(session: AsyncSession, *, hour: LocationHour) -> None:
    await session.delete(hour)
    await session.commit()


async def list_closures(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
) -> list[LocationClosure]:
    await _ensure_location(session, account_id=account_id, location_id=location_id)
    stmt: Select[tuple[LocationClosure]] = (
        select(LocationClosure)
        .where(LocationClosure.location_id == location_id)
        .order_by(LocationClosure.start_date.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def create_closure(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    payload: LocationClosureCreate,
) -> LocationClosure:
    await _ensure_location(session, account_id=account_id, location_id=location_id)
    closure = LocationClosure(
        location_id=location_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
    )
    session.add(closure)
    await session.commit()
    await session.refresh(closure)
    return closure


async def delete_closure(session: AsyncSession, *, closure: LocationClosure) -> None:
    await session.delete(closure)
    await session.commit()
