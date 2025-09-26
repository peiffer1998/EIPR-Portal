"""Payroll period utilities."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CommissionPayout,
    PayRateHistory,
    PayrollPeriod,
    TipShare,
    TipTransaction,
    TimeClockPunch,
)


def _dstart(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=UTC)


def _dend(d: date) -> datetime:
    return datetime.combine(d, time.max, tzinfo=UTC)


async def open_period(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID | None,
    starts_on: date,
    ends_on: date,
) -> PayrollPeriod:
    period = PayrollPeriod(
        account_id=account_id,
        location_id=location_id,
        starts_on=starts_on,
        ends_on=ends_on,
    )
    session.add(period)
    await session.commit()
    await session.refresh(period)
    return period


async def lock_period(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    period_id: uuid.UUID,
) -> PayrollPeriod:
    period = await session.get(PayrollPeriod, period_id)
    if period is None or period.account_id != account_id:
        raise ValueError("Payroll period not found")

    await session.execute(
        update(TimeClockPunch)
        .where(
            TimeClockPunch.account_id == account_id,
            TimeClockPunch.rounded_in_at >= _dstart(period.starts_on),
            TimeClockPunch.rounded_in_at <= _dend(period.ends_on),
        )
        .values(is_locked=True, payroll_period_id=period.id)
    )
    await session.execute(
        update(TipTransaction)
        .where(
            TipTransaction.account_id == account_id,
            TipTransaction.date >= period.starts_on,
            TipTransaction.date <= period.ends_on,
        )
        .values(is_locked=True, payroll_period_id=period.id)
    )
    await session.execute(
        update(CommissionPayout)
        .where(CommissionPayout.account_id == account_id)
        .values(is_locked=True, payroll_period_id=period.id)
    )

    totals_hours: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    totals_wages: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    totals_tips: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    totals_commissions: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    punches = (
        (
            await session.execute(
                select(TimeClockPunch).where(
                    TimeClockPunch.account_id == account_id,
                    TimeClockPunch.rounded_in_at >= _dstart(period.starts_on),
                    TimeClockPunch.rounded_in_at <= _dend(period.ends_on),
                    TimeClockPunch.minutes_worked > 0,
                )
            )
        )
        .scalars()
        .all()
    )

    async def pay_rate(user_id: uuid.UUID, day: date) -> Decimal:
        stmt = (
            select(PayRateHistory)
            .where(
                PayRateHistory.account_id == account_id,
                PayRateHistory.user_id == user_id,
                PayRateHistory.effective_on <= day,
            )
            .order_by(PayRateHistory.effective_on.desc())
            .limit(1)
        )
        row = (await session.execute(stmt)).scalars().first()
        return row.hourly_rate if row else Decimal("0")

    for punch in punches:
        hours = Decimal(punch.minutes_worked) / Decimal(60)
        key = str(punch.user_id)
        totals_hours[key] += hours
        rate = await pay_rate(punch.user_id, punch.rounded_in_at.date())
        totals_wages[key] += (hours * rate).quantize(Decimal("0.01"))

    shares = (
        await session.execute(
            select(TipShare, TipTransaction)
            .join(TipTransaction, TipTransaction.id == TipShare.tip_transaction_id)
            .where(
                TipTransaction.account_id == account_id,
                TipTransaction.date >= period.starts_on,
                TipTransaction.date <= period.ends_on,
            )
        )
    ).all()
    for share, _tx in shares:
        totals_tips[str(share.user_id)] += share.amount

    payouts = (
        (
            await session.execute(
                select(CommissionPayout).where(
                    CommissionPayout.account_id == account_id,
                    CommissionPayout.payroll_period_id == period.id,
                )
            )
        )
        .scalars()
        .all()
    )
    for payout in payouts:
        totals_commissions[str(payout.specialist_id)] += payout.commission_amount

    period.locked_at = datetime.now(UTC)
    period.totals = {
        "hours_by_user": {user: str(total) for user, total in totals_hours.items()},
        "wages_by_user": {user: str(total) for user, total in totals_wages.items()},
        "tips_by_user": {user: str(total) for user, total in totals_tips.items()},
        "commissions_by_specialist": {
            spec: str(total) for spec, total in totals_commissions.items()
        },
        "starts_on": period.starts_on.isoformat(),
        "ends_on": period.ends_on.isoformat(),
    }
    await session.commit()
    await session.refresh(period)
    return period


async def mark_paid(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    period_id: uuid.UUID,
) -> PayrollPeriod:
    period = await session.get(PayrollPeriod, period_id)
    if period is None or period.account_id != account_id:
        raise ValueError("Payroll period not found")
    period.paid_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(period)
    return period
