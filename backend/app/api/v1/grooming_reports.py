"""Grooming analytics endpoints."""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models import GroomingAppointment, User, UserRole
from app.schemas.grooming import GroomingCommissionSummary, GroomingLoadSummary

router = APIRouter()


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def _day_bounds(target: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target, time.min)
    end = datetime.combine(target, time.max)
    return start, end


@router.get("/load", response_model=GroomingLoadSummary, summary="Daily load report")
async def report_load(
    *,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    report_date: date,
    specialist_id: uuid.UUID | None = None,
) -> GroomingLoadSummary:
    _assert_staff(current_user)
    window_start, window_end = _day_bounds(report_date)
    stmt = (
        select(GroomingAppointment)
        .where(
            GroomingAppointment.account_id == current_user.account_id,
            GroomingAppointment.start_at >= window_start,
            GroomingAppointment.start_at <= window_end,
        )
        .options(selectinload(GroomingAppointment.specialist))
    )
    if specialist_id is not None:
        stmt = stmt.where(GroomingAppointment.specialist_id == specialist_id)
    result = await session.execute(stmt)
    appointments = result.scalars().all()

    status_counts: Counter[str] = Counter()
    total_minutes = 0
    for appt in appointments:
        status_counts[appt.status.value] += 1
        duration = appt.end_at - appt.start_at
        total_minutes += max(0, int(duration.total_seconds() // 60))

    return GroomingLoadSummary(
        date=report_date,
        total_minutes=total_minutes,
        status_counts=dict(status_counts),
    )


@router.get(
    "/commissions",
    response_model=list[GroomingCommissionSummary],
    summary="Commission totals",
)
async def report_commissions(
    *,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date,
    date_to: date,
    specialist_id: uuid.UUID | None = None,
) -> list[GroomingCommissionSummary]:
    _assert_staff(current_user)
    if date_from > date_to:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="date_from must be before date_to"
        )

    start = datetime.combine(date_from, time.min)
    end = datetime.combine(date_to, time.max)

    stmt = (
        select(GroomingAppointment)
        .where(
            GroomingAppointment.account_id == current_user.account_id,
            GroomingAppointment.start_at >= start,
            GroomingAppointment.start_at <= end,
            GroomingAppointment.commission_amount.is_not(None),
        )
        .options(selectinload(GroomingAppointment.specialist))
    )
    if specialist_id is not None:
        stmt = stmt.where(GroomingAppointment.specialist_id == specialist_id)

    result = await session.execute(stmt)
    appointments = result.scalars().all()

    counts: defaultdict[uuid.UUID, int] = defaultdict(int)
    totals: defaultdict[uuid.UUID, Decimal] = defaultdict(lambda: Decimal("0"))
    names: dict[uuid.UUID, str | None] = {}

    for appt in appointments:
        if appt.commission_amount is None:
            continue
        totals[appt.specialist_id] += appt.commission_amount
        counts[appt.specialist_id] += 1
        if appt.specialist:
            names[appt.specialist_id] = appt.specialist.name

    summaries: list[GroomingCommissionSummary] = []
    for specialist_key, total in totals.items():
        summaries.append(
            GroomingCommissionSummary(
                specialist_id=specialist_key,
                specialist_name=names.get(specialist_key),
                total_commission=total,
                appointment_count=counts[specialist_key],
            )
        )
    summaries.sort(key=lambda item: item.specialist_name or "")
    return summaries
