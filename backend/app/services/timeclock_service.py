"""Time clock punch in/out with simple rounding."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TimeClockPunch

ROUND_MINUTES = 15  # default site-wide; can be made per-location later
ROUND_MODE = "nearest"  # nearest|up|down


def _coerce_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _round(dt: datetime) -> datetime:
    """Round datetime to the nearest configured interval."""
    q = ROUND_MINUTES
    secs = int(dt.timestamp())
    base = (secs // (q * 60)) * (q * 60)
    rem = secs - base
    if ROUND_MODE == "down":
        r = base
    elif ROUND_MODE == "up":
        r = base + q * 60 if rem else base
    else:
        r = base + (q * 60 if rem >= (q * 60) / 2 else 0)
    return datetime.fromtimestamp(r, tz=UTC)


def _open_punch_stmt(account_id: uuid.UUID, user_id: uuid.UUID):
    return select(TimeClockPunch).where(
        TimeClockPunch.account_id == account_id,
        TimeClockPunch.user_id == user_id,
        TimeClockPunch.clock_out_at.is_(None),
    )


async def punch_in(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    user_id: uuid.UUID,
    at: datetime | None = None,
    source: str = "web",
) -> TimeClockPunch:
    now = _coerce_utc(at or datetime.now(UTC))
    if (await session.execute(_open_punch_stmt(account_id, user_id))).scalars().first():
        raise ValueError("Open punch already exists")
    rounded = _round(now)
    punch = TimeClockPunch(
        account_id=account_id,
        location_id=location_id,
        user_id=user_id,
        clock_in_at=now,
        rounded_in_at=rounded,
        source=source,
        minutes_worked=0,
    )
    session.add(punch)
    await session.commit()
    await session.refresh(punch)
    return punch


async def punch_out(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
    at: datetime | None = None,
) -> TimeClockPunch:
    now = _coerce_utc(at or datetime.now(UTC))
    punch = (
        (await session.execute(_open_punch_stmt(account_id, user_id))).scalars().first()
    )
    if punch is None:
        raise ValueError("No open punch to close")
    rounded_out = _round(now)
    if rounded_out < punch.rounded_in_at:
        rounded_out = punch.rounded_in_at
    minutes = int((rounded_out - punch.rounded_in_at).total_seconds() // 60)
    await session.execute(
        update(TimeClockPunch)
        .where(TimeClockPunch.id == punch.id)
        .values(clock_out_at=now, rounded_out_at=rounded_out, minutes_worked=minutes)
    )
    await session.commit()
    await session.refresh(punch)
    return punch
