"""Scheduling utilities for grooming availability."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Iterable, Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.grooming import (
    GroomingAddon,
    GroomingAppointment,
    GroomingAppointmentStatus,
    GroomingService,
    Specialist,
    SpecialistTimeOff,
)


@dataclass(slots=True, frozen=True)
class AvailableSlot:
    """Discrete start/end window with the specialist assigned."""

    start_at: datetime
    end_at: datetime
    specialist_id: uuid.UUID


_BLOCKING_STATUSES: set[GroomingAppointmentStatus] = {
    GroomingAppointmentStatus.REQUESTED,
    GroomingAppointmentStatus.SCHEDULED,
    GroomingAppointmentStatus.CHECKED_IN,
    GroomingAppointmentStatus.IN_PROGRESS,
    GroomingAppointmentStatus.COMPLETED,
}


async def _load_service(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    service_id: uuid.UUID,
) -> GroomingService:
    service = await session.get(GroomingService, service_id)
    if service is None or service.account_id != account_id or not service.active:
        raise ValueError("Grooming service unavailable for account")
    return service


async def _load_addons(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    addon_ids: Sequence[uuid.UUID],
) -> list[GroomingAddon]:
    if not addon_ids:
        return []
    stmt: Select[tuple[GroomingAddon]] = select(GroomingAddon).where(
        GroomingAddon.id.in_(addon_ids),
        GroomingAddon.account_id == account_id,
        GroomingAddon.active.is_(True),
    )
    result = await session.execute(stmt)
    addons = result.scalars().all()
    if len(addons) != len(set(addon_ids)):
        raise ValueError("One or more add-ons are invalid for this account")
    return list(addons)


async def _load_specialists(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    specialist_id: uuid.UUID | None,
) -> list[Specialist]:
    stmt: Select[tuple[Specialist]] = (
        select(Specialist)
        .options(
            selectinload(Specialist.schedules),
            selectinload(Specialist.time_off_entries),
        )
        .where(
            Specialist.account_id == account_id,
            Specialist.location_id == location_id,
            Specialist.active.is_(True),
        )
    )
    if specialist_id is not None:
        stmt = stmt.where(Specialist.id == specialist_id)
    result = await session.execute(stmt)
    specialists = result.scalars().unique().all()
    if specialist_id is not None and not specialists:
        raise ValueError("Specialist not found for account/location")
    return list(specialists)


async def _load_time_off(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    specialist_ids: Sequence[uuid.UUID],
    range_start: datetime,
    range_end: datetime,
) -> dict[uuid.UUID, list[tuple[datetime, datetime]]]:
    if not specialist_ids:
        return {}
    stmt: Select[tuple[SpecialistTimeOff]] = select(SpecialistTimeOff).where(
        SpecialistTimeOff.account_id == account_id,
        SpecialistTimeOff.specialist_id.in_(specialist_ids),
        SpecialistTimeOff.ends_at >= range_start,
        SpecialistTimeOff.starts_at <= range_end,
    )
    result = await session.execute(stmt)
    records = result.scalars().all()
    grouped: dict[uuid.UUID, list[tuple[datetime, datetime]]] = {}
    for entry in records:
        grouped.setdefault(entry.specialist_id, []).append(
            (entry.starts_at, entry.ends_at)
        )
    return grouped


async def _load_appointments(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    specialist_ids: Sequence[uuid.UUID],
    range_start: datetime,
    range_end: datetime,
) -> dict[uuid.UUID, list[tuple[datetime, datetime]]]:
    if not specialist_ids:
        return {}
    stmt: Select[tuple[GroomingAppointment]] = select(GroomingAppointment).where(
        GroomingAppointment.account_id == account_id,
        GroomingAppointment.specialist_id.in_(specialist_ids),
        GroomingAppointment.end_at >= range_start,
        GroomingAppointment.start_at <= range_end,
        GroomingAppointment.status.in_(_BLOCKING_STATUSES),
    )
    result = await session.execute(stmt)
    appointments = result.scalars().all()
    grouped: dict[uuid.UUID, list[tuple[datetime, datetime]]] = {}
    for appt in appointments:
        grouped.setdefault(appt.specialist_id, []).append((appt.start_at, appt.end_at))
    return grouped


def _normalize_datetime(candidate: datetime) -> datetime:
    if candidate.tzinfo is None:
        return candidate.replace(tzinfo=UTC)
    return candidate.astimezone(UTC)


def _generate_slots_for_block(
    block_start: datetime,
    block_end: datetime,
    *,
    duration: timedelta,
    interval: timedelta,
    blocked: Iterable[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    slots: list[tuple[datetime, datetime]] = []
    blocked_windows = [
        (
            _normalize_datetime(start),
            _normalize_datetime(end),
        )
        for start, end in blocked
    ]
    cursor = block_start
    while cursor + duration <= block_end:
        candidate_end = cursor + duration
        overlaps = False
        for busy_start, busy_end in blocked_windows:
            if not (candidate_end <= busy_start or cursor >= busy_end):
                overlaps = True
                break
        if not overlaps:
            slots.append((cursor, candidate_end))
        cursor += interval
    return slots


async def list_available_slots(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    date_from: date,
    date_to: date,
    service_id: uuid.UUID,
    addon_ids: Sequence[uuid.UUID] | None = None,
    specialist_id: uuid.UUID | None = None,
    slot_interval_minutes: int = 15,
) -> list[AvailableSlot]:
    if date_from > date_to:
        raise ValueError("date_from must be on or before date_to")
    if slot_interval_minutes <= 0:
        raise ValueError("slot_interval_minutes must be positive")

    service = await _load_service(session, account_id=account_id, service_id=service_id)
    addons = await _load_addons(
        session,
        account_id=account_id,
        addon_ids=addon_ids or [],
    )
    total_minutes = service.base_duration_minutes + sum(
        addon.add_duration_minutes for addon in addons
    )
    duration = timedelta(minutes=total_minutes)
    interval = timedelta(minutes=slot_interval_minutes)

    specialists = await _load_specialists(
        session,
        account_id=account_id,
        location_id=location_id,
        specialist_id=specialist_id,
    )
    specialist_ids = [spec.id for spec in specialists]
    if not specialist_ids:
        return []

    range_start = datetime.combine(date_from, time.min, tzinfo=UTC)
    range_end = datetime.combine(date_to, time.max, tzinfo=UTC)

    time_off = await _load_time_off(
        session,
        account_id=account_id,
        specialist_ids=specialist_ids,
        range_start=range_start,
        range_end=range_end,
    )
    appointments = await _load_appointments(
        session,
        account_id=account_id,
        specialist_ids=specialist_ids,
        range_start=range_start,
        range_end=range_end,
    )

    available: list[AvailableSlot] = []
    current_date = date_from
    while current_date <= date_to:
        weekday = current_date.weekday()
        for specialist in specialists:
            schedules = [
                schedule
                for schedule in specialist.schedules
                if schedule.weekday == weekday
            ]
            if not schedules:
                continue
            busy = appointments.get(specialist.id, []) + time_off.get(specialist.id, [])
            for schedule in schedules:
                block_start = datetime.combine(
                    current_date,
                    schedule.start_time,
                    tzinfo=UTC,
                )
                block_end = datetime.combine(
                    current_date,
                    schedule.end_time,
                    tzinfo=UTC,
                )
                if block_end <= block_start:
                    continue
                raw_slots = _generate_slots_for_block(
                    _normalize_datetime(block_start),
                    _normalize_datetime(block_end),
                    duration=duration,
                    interval=interval,
                    blocked=busy,
                )
                available.extend(
                    AvailableSlot(
                        start_at=start, end_at=end, specialist_id=specialist.id
                    )
                    for start, end in raw_slots
                )
        current_date += timedelta(days=1)
    available.sort(key=lambda slot: (slot.start_at, slot.specialist_id))
    return available
