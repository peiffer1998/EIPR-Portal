"""Commission payouts from completed grooming appointments."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CommissionPayout
from app.models.grooming import (
    GroomingAppointment,
    GroomingAppointmentStatus,
    Specialist,
)


def _to_money(value: Decimal | float | str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _day(d: date, end: bool = False) -> datetime:
    return datetime.combine(d, time.max if end else time.min, tzinfo=UTC)


async def build_from_completed_appointments(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    date_from: date,
    date_to: date,
    location_id: uuid.UUID | None = None,
) -> int:
    """Create CommissionPayout rows for completed appointments without one."""
    stmt = (
        select(GroomingAppointment)
        .where(
            GroomingAppointment.account_id == account_id,
            GroomingAppointment.status == GroomingAppointmentStatus.COMPLETED,
            GroomingAppointment.start_at >= _day(date_from),
            GroomingAppointment.start_at <= _day(date_to, end=True),
            GroomingAppointment.commission_amount.is_not(None),
        )
        .options(selectinload(GroomingAppointment.specialist))
    )
    if location_id is not None:
        stmt = stmt.where(
            GroomingAppointment.specialist.has(location_id=location_id)  # type: ignore[arg-type]
        )

    created = 0
    for appointment in (await session.execute(stmt)).scalars():
        exists = await session.execute(
            select(CommissionPayout.id).where(
                CommissionPayout.appointment_id == appointment.id
            )
        )
        if exists.first():
            continue
        commission_amount = _to_money(appointment.commission_amount or 0)
        specialist_location_id = None
        if appointment.specialist is not None:
            specialist_location_id = appointment.specialist.location_id
        else:
            location_row = await session.execute(
                select(Specialist.location_id).where(
                    Specialist.id == appointment.specialist_id
                )
            )
            specialist_location_id = location_row.scalar_one_or_none()

        if specialist_location_id is None:
            # Specialist was removed or misconfigured; skip until data is corrected.
            continue

        payout = CommissionPayout(
            account_id=appointment.account_id,
            location_id=specialist_location_id,
            appointment_id=appointment.id,
            specialist_id=appointment.specialist_id,
            basis_amount=appointment.price_snapshot,
            commission_amount=commission_amount,
            snapshot={
                "price_snapshot": str(appointment.price_snapshot or ""),
                "commission_type": str(appointment.commission_type or ""),
                "commission_rate": str(appointment.commission_rate or ""),
            },
        )
        session.add(payout)
        created += 1
    await session.commit()
    return created
