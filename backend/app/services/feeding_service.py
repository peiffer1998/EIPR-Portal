"""Feeding schedule services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.feeding_schedule import FeedingSchedule
from app.models.reservation import Reservation
from app.schemas.feeding import FeedingScheduleCreate, FeedingScheduleUpdate


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


async def _ensure_reservation(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> Reservation:
    reservation = await session.get(Reservation, reservation_id)
    if reservation is None or reservation.account_id != account_id:
        raise ValueError("Reservation not found for account")
    return reservation


async def list_feeding_schedules(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> list[FeedingSchedule]:
    await _ensure_reservation(
        session, account_id=account_id, reservation_id=reservation_id
    )
    stmt: Select[tuple[FeedingSchedule]] = (
        select(FeedingSchedule)
        .where(FeedingSchedule.reservation_id == reservation_id)
        .order_by(FeedingSchedule.scheduled_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_feeding_schedule(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    schedule_id: uuid.UUID,
) -> FeedingSchedule | None:
    stmt = (
        select(FeedingSchedule)
        .join(Reservation)
        .options(selectinload(FeedingSchedule.reservation))
        .where(FeedingSchedule.id == schedule_id, Reservation.account_id == account_id)
    )
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def create_feeding_schedule(
    session: AsyncSession,
    payload: FeedingScheduleCreate,
    *,
    account_id: uuid.UUID,
) -> FeedingSchedule:
    await _ensure_reservation(
        session, account_id=account_id, reservation_id=payload.reservation_id
    )
    schedule = FeedingSchedule(
        reservation_id=payload.reservation_id,
        scheduled_at=_coerce_utc(payload.scheduled_at),
        food=payload.food,
        quantity=payload.quantity,
        notes=payload.notes,
    )
    session.add(schedule)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(schedule)
    return schedule


async def update_feeding_schedule(
    session: AsyncSession,
    *,
    schedule: FeedingSchedule,
    account_id: uuid.UUID,
    payload: FeedingScheduleUpdate,
) -> FeedingSchedule:
    await session.refresh(schedule, attribute_names=["reservation"])
    if schedule.reservation.account_id != account_id:
        raise ValueError("Schedule does not belong to the provided account")

    updates = payload.model_dump(exclude_unset=True)
    if "scheduled_at" in updates:
        schedule.scheduled_at = _coerce_utc(updates["scheduled_at"])
    if "food" in updates:
        schedule.food = updates["food"]
    if "quantity" in updates:
        schedule.quantity = updates["quantity"]
    if "notes" in updates:
        schedule.notes = updates["notes"]

    await session.commit()
    await session.refresh(schedule)
    return schedule


async def delete_feeding_schedule(
    session: AsyncSession,
    *,
    schedule: FeedingSchedule,
    account_id: uuid.UUID,
) -> None:
    await session.refresh(schedule, attribute_names=["reservation"])
    if schedule.reservation.account_id != account_id:
        raise ValueError("Schedule does not belong to the provided account")
    await session.delete(schedule)
    await session.commit()
