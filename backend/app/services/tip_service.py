"""Tip recording and allocation."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TipPolicy, TipShare, TipTransaction, TimeClockPunch
from app.models.grooming import GroomingAppointment


def _to_money(value: Decimal | float | str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, time.min, tzinfo=UTC)
    end = datetime.combine(d + timedelta(days=1), time.min, tzinfo=UTC)
    return start, end


async def _hours_for_day(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    d: date,
) -> dict[uuid.UUID, Decimal]:
    start, end = _day_bounds(d)
    stmt = select(TimeClockPunch).where(
        TimeClockPunch.account_id == account_id,
        TimeClockPunch.location_id == location_id,
        TimeClockPunch.rounded_in_at < end,
        TimeClockPunch.rounded_out_at.is_not(None),
        TimeClockPunch.rounded_out_at > start,
    )
    totals: dict[uuid.UUID, int] = defaultdict(int)
    for punch in (await session.execute(stmt)).scalars():
        rin_raw = punch.rounded_in_at
        rout_raw = punch.rounded_out_at or start
        if rin_raw.tzinfo is None:
            rin_raw = rin_raw.replace(tzinfo=UTC)
        if rout_raw.tzinfo is None:
            rout_raw = rout_raw.replace(tzinfo=UTC)
        rin = max(rin_raw, start)
        rout = min(rout_raw, end)
        minutes = max(0, int((rout - rin).total_seconds() // 60))
        totals[punch.user_id] += minutes
    return {
        user_id: Decimal(minutes) / Decimal(60) for user_id, minutes in totals.items()
    }


async def record_tip(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    d: date,
    amount: Decimal,
    policy: TipPolicy,
    recipients: list[tuple[uuid.UUID, Decimal]] | None = None,
    appointment_id: uuid.UUID | None = None,
    payment_transaction_id: uuid.UUID | None = None,
    note: str | None = None,
) -> TipTransaction:
    amount = _to_money(amount)
    tx = TipTransaction(
        account_id=account_id,
        location_id=location_id,
        date=d,
        amount=amount,
        policy=policy,
        appointment_id=appointment_id,
        payment_transaction_id=payment_transaction_id,
        note=note,
    )
    session.add(tx)
    await session.flush()

    shares: list[tuple[uuid.UUID, Decimal]] = []
    if policy == TipPolicy.DIRECT_TO_STAFF:
        if not recipients:
            raise ValueError("Recipients required for direct_to_staff policy")
        shares = [(uid, _to_money(amt)) for uid, amt in recipients]
    elif policy == TipPolicy.POOLED_EQUAL:
        hours = await _hours_for_day(
            session, account_id=account_id, location_id=location_id, d=d
        )
        if not hours:
            raise ValueError("No eligible staff for pooled equal tip")
        users = sorted(hours.keys(), key=lambda u: str(u))
        each = (amount / len(users)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        remainder = amount - each * len(users)
        for idx, user_id in enumerate(users):
            shares.append((user_id, each + (remainder if idx == 0 else Decimal("0"))))
    elif policy == TipPolicy.POOLED_BY_HOURS:
        hours = await _hours_for_day(
            session, account_id=account_id, location_id=location_id, d=d
        )
        total_hours = sum(hours.values())
        if total_hours <= 0:
            raise ValueError("No hours recorded for pooled_by_hours tip")
        sorted_items = sorted(hours.items(), key=lambda item: str(item[0]))
        allocated = Decimal("0")
        for user_id, hours_worked in sorted_items:
            portion = (amount * (hours_worked / total_hours)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            allocated += portion
            shares.append((user_id, portion))
        remainder = amount - allocated
        if shares and remainder:
            first_user_id, first_amount = shares[0]
            shares[0] = (first_user_id, _to_money(first_amount + remainder))
    elif policy == TipPolicy.APPOINTMENT_DIRECT:
        if not appointment_id:
            raise ValueError("appointment_id required for appointment_direct policy")
        appointment = await session.get(GroomingAppointment, appointment_id)
        if appointment is None or appointment.account_id != account_id:
            raise ValueError("Appointment not found for account")
        if appointment.specialist is None or appointment.specialist.user_id is None:
            raise ValueError("Specialist has no linked user")
        shares = [(appointment.specialist.user_id, amount)]
    else:
        raise ValueError("Unsupported tip policy")

    for user_id, share_amount in shares:
        session.add(
            TipShare(
                tip_transaction_id=tx.id,
                user_id=user_id,
                amount=_to_money(share_amount),
                method=policy.value,
            )
        )
    await session.commit()
    await session.refresh(tx)
    return tx
