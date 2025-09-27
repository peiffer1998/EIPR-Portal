"""Extended CSV reporting services (Phase 16)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Deposit,
    Invoice,
    InvoiceStatus,
    Location,
    PaymentTransaction,
    Reservation,
    ReservationType,
    Specialist,
    GroomingAppointment,
    TipShare,
    TipTransaction,
    Pet,
)


def _day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _day_end(value: date) -> datetime:
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=UTC)


def _serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(getattr(value, "value", value))


def _validate_range(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        msg = "start_date must be on or before end_date"
        raise ValueError(msg)


async def revenue_by_date(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
    location_id: uuid.UUID | None = None,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    stmt = (
        select(
            func.date(Invoice.paid_at).label("paid_date"),
            Location.id,
            Location.name,
            Reservation.reservation_type,
            func.sum(Invoice.subtotal).label("subtotal"),
            func.sum(Invoice.discount_total).label("discounts"),
            func.sum(Invoice.tax_total).label("tax"),
            func.sum(Invoice.total).label("total"),
        )
        .join(Reservation, Reservation.id == Invoice.reservation_id)
        .join(Location, Location.id == Reservation.location_id)
        .where(
            Invoice.account_id == account_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.paid_at >= _day_start(start_date),
            Invoice.paid_at < _day_end(end_date),
        )
        .group_by("paid_date", Location.id, Location.name, Reservation.reservation_type)
        .order_by("paid_date", Location.name, Reservation.reservation_type)
    )
    if location_id:
        stmt = stmt.where(Location.id == location_id)

    rows = (await session.execute(stmt)).all()

    output: list[list[str]] = [
        [
            "date",
            "location_id",
            "location_name",
            "service_type",
            "subtotal",
            "discounts",
            "tax",
            "total",
        ]
    ]
    for paid_date, loc_id, loc_name, res_type, subtotal, discounts, tax, total in rows:
        output.append(
            [
                _serialize(paid_date),
                _serialize(loc_id),
                _serialize(loc_name),
                _serialize(res_type),
                _serialize(subtotal),
                _serialize(discounts),
                _serialize(tax),
                _serialize(total),
            ]
        )
    return output


async def sales_tax_by_date(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
    location_id: uuid.UUID | None = None,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    stmt = (
        select(
            func.date(Invoice.paid_at).label("paid_date"),
            Location.id,
            Location.name,
            func.sum(Invoice.tax_total).label("tax_total"),
        )
        .join(Reservation, Reservation.id == Invoice.reservation_id)
        .join(Location, Location.id == Reservation.location_id)
        .where(
            Invoice.account_id == account_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.paid_at >= _day_start(start_date),
            Invoice.paid_at < _day_end(end_date),
        )
        .group_by("paid_date", Location.id, Location.name)
        .order_by("paid_date", Location.name)
    )
    if location_id:
        stmt = stmt.where(Location.id == location_id)

    rows = (await session.execute(stmt)).all()

    output: list[list[str]] = [
        ["date", "location_id", "location_name", "tax_code", "tax_total"]
    ]
    for paid_date, loc_id, loc_name, tax_total in rows:
        output.append(
            [
                _serialize(paid_date),
                _serialize(loc_id),
                _serialize(loc_name),
                "default",
                _serialize(tax_total),
            ]
        )
    return output


async def payments_by_method(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    stmt = (
        select(
            func.date(PaymentTransaction.created_at).label("day"),
            PaymentTransaction.provider,
            PaymentTransaction.status,
            func.count(PaymentTransaction.id),
            func.sum(PaymentTransaction.amount),
        )
        .where(
            PaymentTransaction.account_id == account_id,
            PaymentTransaction.created_at >= _day_start(start_date),
            PaymentTransaction.created_at < _day_end(end_date),
        )
        .group_by("day", PaymentTransaction.provider, PaymentTransaction.status)
        .order_by("day", PaymentTransaction.provider, PaymentTransaction.status)
    )

    rows = (await session.execute(stmt)).all()

    output: list[list[str]] = [["date", "provider", "status", "count", "amount"]]
    for day, provider, status, count_value, amount in rows:
        output.append(
            [
                _serialize(day),
                _serialize(provider),
                _serialize(status),
                _serialize(count_value),
                _serialize(amount),
            ]
        )
    return output


async def discounts_by_date(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    stmt = (
        select(
            func.date(Invoice.paid_at).label("day"),
            func.sum(Invoice.discount_total),
        )
        .where(
            Invoice.account_id == account_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.paid_at >= _day_start(start_date),
            Invoice.paid_at < _day_end(end_date),
        )
        .group_by("day")
        .order_by("day")
    )

    rows = (await session.execute(stmt)).all()

    output: list[list[str]] = [["date", "discount_total"]]
    for day, discount_total in rows:
        output.append(
            [
                _serialize(day),
                _serialize(discount_total),
            ]
        )
    return output


async def deposits_summary(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    stmt = (
        select(
            func.date(Deposit.created_at).label("day"),
            Deposit.status,
            func.count(Deposit.id),
            func.sum(Deposit.amount),
        )
        .where(
            Deposit.account_id == account_id,
            Deposit.created_at >= _day_start(start_date),
            Deposit.created_at < _day_end(end_date),
        )
        .group_by("day", Deposit.status)
        .order_by("day", Deposit.status)
    )

    rows = (await session.execute(stmt)).all()

    output: list[list[str]] = [["date", "status", "count", "amount"]]
    for day, status, count_value, amount in rows:
        output.append(
            [
                _serialize(day),
                _serialize(status),
                _serialize(count_value),
                _serialize(amount),
            ]
        )
    return output


async def invoices_aging(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    as_of: date,
) -> list[list[str]]:
    reference = _day_end(as_of)
    age_days = func.extract("epoch", reference - Invoice.created_at) / 86400.0
    buckets = case(
        (age_days <= 30, "0-30"),
        (age_days <= 60, "31-60"),
        (age_days <= 90, "61-90"),
        else_="90+",
    )

    stmt = (
        select(
            buckets.label("bucket"),
            func.count(Invoice.id),
            func.sum(Invoice.total),
        )
        .where(
            Invoice.account_id == account_id,
            Invoice.status == InvoiceStatus.PENDING,
        )
        .group_by("bucket")
        .order_by("bucket")
    )

    rows = (await session.execute(stmt)).all()

    output: list[list[str]] = [["bucket", "open_invoices", "total"]]
    for bucket, count_value, total in rows:
        output.append(
            [
                _serialize(bucket),
                _serialize(count_value),
                _serialize(total),
            ]
        )
    return output


async def new_vs_repeat_customers(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    first_reservation_subq = (
        select(
            Pet.owner_id.label("owner_id"),
            func.min(func.date(Reservation.start_at)).label("first_date"),
        )
        .join(Pet, Pet.id == Reservation.pet_id)
        .where(Reservation.account_id == account_id)
        .group_by(Pet.owner_id)
        .subquery()
    )

    daily_owner_subq = (
        select(
            func.date(Reservation.start_at).label("day"),
            Pet.owner_id.label("owner_id"),
        )
        .join(Pet, Pet.id == Reservation.pet_id)
        .where(
            Reservation.account_id == account_id,
            Reservation.start_at >= _day_start(start_date),
            Reservation.start_at < _day_end(end_date),
        )
        .group_by(func.date(Reservation.start_at), Pet.owner_id)
        .subquery()
    )

    stmt = select(
        daily_owner_subq.c.day,
        first_reservation_subq.c.first_date,
    ).join(
        first_reservation_subq,
        first_reservation_subq.c.owner_id == daily_owner_subq.c.owner_id,
    )

    rows = (await session.execute(stmt)).all()

    new_counts: dict[date, int] = defaultdict(int)
    repeat_counts: dict[date, int] = defaultdict(int)

    for day_value, first_date in rows:
        if day_value is None or first_date is None:
            continue
        if day_value == first_date:
            new_counts[day_value] += 1
        else:
            repeat_counts[day_value] += 1

    all_days = sorted(set(new_counts) | set(repeat_counts))
    output: list[list[str]] = [["date", "new_customers", "repeat_customers"]]
    for day_value in all_days:
        output.append(
            [
                _serialize(day_value),
                _serialize(new_counts.get(day_value, 0)),
                _serialize(repeat_counts.get(day_value, 0)),
            ]
        )
    return output


async def reservations_status_summary(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
    location_id: uuid.UUID | None = None,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    stmt = (
        select(
            func.date(Reservation.start_at).label("day"),
            Reservation.status,
            func.count(Reservation.id),
        )
        .where(
            Reservation.account_id == account_id,
            Reservation.start_at >= _day_start(start_date),
            Reservation.start_at < _day_end(end_date),
        )
        .group_by("day", Reservation.status)
        .order_by("day", Reservation.status)
    )
    if location_id:
        stmt = stmt.where(Reservation.location_id == location_id)

    rows = (await session.execute(stmt)).all()

    output: list[list[str]] = [["date", "status", "count"]]
    for day_value, status, count_value in rows:
        output.append(
            [
                _serialize(day_value),
                _serialize(status),
                _serialize(count_value),
            ]
        )
    return output


async def occupancy_csv(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
    location_id: uuid.UUID | None = None,
    reservation_type: ReservationType | None = None,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    try:
        from app.services.reporting_service import occupancy_report

        entries = await occupancy_report(
            session,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            location_id=location_id,
            reservation_type=reservation_type,
        )
        output: list[list[str]] = [
            [
                "date",
                "location_id",
                "location_name",
                "reservation_type",
                "capacity",
                "booked",
                "available",
                "occupancy_rate",
            ]
        ]
        for entry in entries:
            output.append(
                [
                    _serialize(entry.get("date")),
                    _serialize(entry.get("location_id")),
                    _serialize(entry.get("location_name")),
                    _serialize(entry.get("reservation_type")),
                    _serialize(entry.get("capacity")),
                    _serialize(entry.get("booked")),
                    _serialize(entry.get("available")),
                    _serialize(entry.get("occupancy_rate")),
                ]
            )
        return output
    except Exception:  # pragma: no cover - defensive fallback
        stmt = (
            select(
                func.date(Reservation.start_at).label("day"),
                func.count(Reservation.id),
            )
            .where(
                Reservation.account_id == account_id,
                Reservation.start_at >= _day_start(start_date),
                Reservation.start_at < _day_end(end_date),
            )
            .group_by("day")
            .order_by("day")
        )
        rows = (await session.execute(stmt)).all()
        output = [["date", "booked"]]
        for day_value, count_value in rows:
            output.append(
                [
                    _serialize(day_value),
                    _serialize(count_value),
                ]
            )
        return output


async def grooming_commissions_csv(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
    specialist_id: uuid.UUID | None = None,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    stmt = (
        select(
            Specialist.id,
            Specialist.name,
            func.count(GroomingAppointment.id),
            func.sum(GroomingAppointment.commission_amount),
        )
        .join(Specialist, Specialist.id == GroomingAppointment.specialist_id)
        .where(
            GroomingAppointment.account_id == account_id,
            GroomingAppointment.start_at >= _day_start(start_date),
            GroomingAppointment.start_at < _day_end(end_date),
            GroomingAppointment.commission_amount.is_not(None),
        )
        .group_by(Specialist.id, Specialist.name)
        .order_by(Specialist.name.asc())
    )
    if specialist_id:
        stmt = stmt.where(GroomingAppointment.specialist_id == specialist_id)

    rows = (await session.execute(stmt)).all()

    output: list[list[str]] = [
        [
            "specialist_id",
            "specialist_name",
            "appointment_count",
            "total_commission",
        ]
    ]
    for spec_id, spec_name, count_value, total in rows:
        output.append(
            [
                _serialize(spec_id),
                _serialize(spec_name),
                _serialize(count_value),
                _serialize(total),
            ]
        )
    return output


async def tips_by_user_and_day(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[list[str]]:
    _validate_range(start_date, end_date)

    stmt = (
        select(
            TipTransaction.date.label("day"),
            TipShare.user_id,
            func.sum(TipShare.amount).label("total"),
        )
        .join(TipShare, TipShare.tip_transaction_id == TipTransaction.id)
        .where(
            TipTransaction.account_id == account_id,
            TipTransaction.date >= start_date,
            TipTransaction.date <= end_date,
        )
        .group_by("day", TipShare.user_id)
        .order_by("day", TipShare.user_id)
    )

    rows = (await session.execute(stmt)).all()

    output: list[list[str]] = [["date", "user_id", "tip_total"]]
    for day_value, user_id, total in rows:
        output.append(
            [
                _serialize(day_value),
                _serialize(user_id),
                _serialize(total),
            ]
        )
    return output


async def not_implemented_csv(*_: Any, **__: Any) -> list[list[str]]:
    return [["message"], ["Not implemented in this build"]]
