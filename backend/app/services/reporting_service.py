"""Reporting and analytics services."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.reservation import Reservation, ReservationStatus, ReservationType
import app.services.reservation_service as reservation_service


async def occupancy_report(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
    location_id: uuid.UUID | None = None,
    reservation_type: ReservationType | None = None,
) -> list[dict[str, Any]]:
    """Return daily occupancy entries grouped by location and reservation type."""
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")

    location_stmt = select(Location).where(Location.account_id == account_id)
    if location_id is not None:
        location_stmt = location_stmt.where(Location.id == location_id)
    locations_result = await session.execute(location_stmt)
    locations = list(locations_result.scalars().all())

    entries: list[dict[str, Any]] = []
    types = [reservation_type] if reservation_type else list(ReservationType)

    for location in locations:
        for res_type in types:
            availability = await reservation_service.get_daily_availability(
                session,
                account_id=account_id,
                location_id=location.id,
                reservation_type=res_type,
                start_date=start_date,
                end_date=end_date,
            )
            for day in availability:
                capacity = day.capacity if day.capacity is not None else None
                booked = int(day.booked)
                available = day.available if day.available is not None else None

                occupancy_rate: float | None = None
                if capacity is not None and capacity > 0:
                    occupancy_rate = round(booked / capacity, 2)

                entries.append(
                    {
                        "location_id": location.id,
                        "location_name": location.name,
                        "reservation_type": res_type,
                        "date": day.date,
                        "capacity": capacity,
                        "booked": booked,
                        "available": available,
                        "occupancy_rate": occupancy_rate,
                    }
                )
    return entries


async def revenue_report(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
    location_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Aggregate monthly revenue totals for completed reservations."""
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")

    start_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
    end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)

    stmt = select(
        Reservation.location_id, Reservation.end_at, Reservation.base_rate
    ).where(
        Reservation.account_id == account_id,
        Reservation.status == ReservationStatus.CHECKED_OUT,
        Reservation.end_at >= start_dt,
        Reservation.end_at < end_dt,
    )
    if location_id is not None:
        stmt = stmt.where(Reservation.location_id == location_id)

    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return {"entries": [], "grand_total": Decimal("0")}

    location_stmt = select(Location.id, Location.name).where(
        Location.account_id == account_id
    )
    location_map = {
        loc_id: name for loc_id, name in (await session.execute(location_stmt)).all()
    }

    totals: dict[tuple[uuid.UUID, date], Decimal] = defaultdict(lambda: Decimal("0"))
    for location_id_value, end_at, base_rate in rows:
        if base_rate is None:
            continue
        month_start = date(end_at.year, end_at.month, 1)
        totals[(location_id_value, month_start)] += Decimal(base_rate)

    entries = [
        {
            "location_id": loc_id,
            "location_name": location_map.get(loc_id, "Unknown"),
            "period_start": period,
            "total_revenue": total.quantize(Decimal("0.01")),
        }
        for (loc_id, period), total in sorted(
            totals.items(), key=lambda item: (item[0][1], item[0][0])
        )
    ]
    grand_total = sum((entry["total_revenue"] for entry in entries), Decimal("0"))
    return {"entries": entries, "grand_total": grand_total.quantize(Decimal("0.01"))}
