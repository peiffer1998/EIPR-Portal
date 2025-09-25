"""Pricing engine utilities for reservations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pricing import PriceRule, PriceRuleType
from app.models.reservation import Reservation

_CURRENCY_QUANT = Decimal("0.01")


@dataclass(slots=True)
class QuoteLine:
    """Individual line used in pricing totals."""

    description: str
    amount: Decimal
    rule_id: uuid.UUID | None = None
    rule_type: PriceRuleType | None = None


@dataclass(slots=True)
class PricingQuote:
    """Aggregated pricing response."""

    reservation_id: uuid.UUID
    account_id: uuid.UUID
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    lines: list[QuoteLine]


class ReservationNotFoundError(RuntimeError):
    """Raised when a reservation cannot be located."""


async def quote_reservation(
    session: AsyncSession,
    *,
    reservation_id: uuid.UUID,
    as_of: date | None = None,
) -> PricingQuote:
    """Build a quote for the supplied reservation."""

    reservation = await session.get(
        Reservation,
        reservation_id,
        options=[selectinload(Reservation.account)],
    )
    if reservation is None:
        raise ReservationNotFoundError("Reservation not found")

    as_of = as_of or reservation.start_at.date()
    base_line = QuoteLine(
        description="Base rate", amount=_quantize(reservation.base_rate)
    )

    rule_stmt = (
        select(PriceRule)
        .where(
            PriceRule.account_id == reservation.account_id,
            PriceRule.active.is_(True),
        )
        .order_by(PriceRule.created_at.asc())
    )
    result = await session.execute(rule_stmt)
    rules = list(result.scalars())

    lines: list[QuoteLine] = [base_line]
    for rule in rules:
        amount = _apply_rule(rule, reservation, as_of)
        if amount == Decimal("0"):
            continue
        description = (
            rule.params.get("description") if isinstance(rule.params, dict) else None
        )
        lines.append(
            QuoteLine(
                description=description or _default_description(rule.rule_type),
                amount=_quantize(amount),
                rule_id=rule.id,
                rule_type=rule.rule_type,
            )
        )

    subtotal = _quantize(
        sum((line.amount for line in lines if line.amount >= 0), Decimal("0"))
    )
    discount_total = _quantize(
        sum((-line.amount for line in lines if line.amount < 0), Decimal("0"))
    )
    taxable_total = subtotal - discount_total
    tax_total = Decimal("0.00")
    total = _quantize(taxable_total + tax_total)

    return PricingQuote(
        reservation_id=reservation.id,
        account_id=reservation.account_id,
        subtotal=subtotal,
        discount_total=discount_total,
        tax_total=tax_total,
        total=total,
        lines=lines,
    )


def _apply_rule(rule: PriceRule, reservation: Reservation, as_of: date) -> Decimal:
    params = rule.params if isinstance(rule.params, dict) else {}
    if rule.rule_type is PriceRuleType.PEAK_DATE:
        return _apply_peak_date(rule, reservation, params, as_of)
    if rule.rule_type is PriceRuleType.LATE_CHECKOUT:
        return _apply_late_checkout(rule, reservation, params)
    if rule.rule_type is PriceRuleType.LODGING_SURCHARGE:
        return _apply_lodging_surcharge(rule, reservation, params)
    if rule.rule_type is PriceRuleType.VIP:
        return _apply_vip(rule, reservation, params)
    return Decimal("0")


def _parse_decimal(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        return default


def _apply_peak_date(
    rule: PriceRule,
    reservation: Reservation,
    params: dict[str, Any],
    as_of: date,
) -> Decimal:
    start_value = params.get("start_date")
    end_value = params.get("end_date")
    if not start_value or not end_value:
        return Decimal("0")
    try:
        start_date = date.fromisoformat(str(start_value))
        end_date = date.fromisoformat(str(end_value))
    except ValueError:
        return Decimal("0")
    if start_date <= as_of <= end_date:
        return _parse_decimal(params.get("amount"))
    return Decimal("0")


def _apply_late_checkout(
    rule: PriceRule,
    reservation: Reservation,
    params: dict[str, Any],
) -> Decimal:
    threshold_hour = params.get("after_hour")
    amount_value = params.get("amount")
    if threshold_hour is None or amount_value is None:
        return Decimal("0")
    try:
        threshold_hour_int = int(threshold_hour)
    except (TypeError, ValueError):
        return Decimal("0")
    end_at = (
        reservation.end_at.astimezone(UTC)
        if reservation.end_at.tzinfo
        else reservation.end_at
    )
    if end_at.hour >= threshold_hour_int:
        return _parse_decimal(amount_value)
    return Decimal("0")


def _apply_lodging_surcharge(
    rule: PriceRule,
    reservation: Reservation,
    params: dict[str, Any],
) -> Decimal:
    percent_value = params.get("percent")
    if percent_value is None:
        return Decimal("0")
    percent = _parse_decimal(percent_value)
    if percent <= 0:
        return Decimal("0")
    surcharge = reservation.base_rate * (percent / Decimal("100"))
    return surcharge


def _apply_vip(
    rule: PriceRule,
    reservation: Reservation,
    params: dict[str, Any],
) -> Decimal:
    percent_value = params.get("percent")
    amount_value = params.get("amount")
    if percent_value is not None:
        percent = _parse_decimal(percent_value)
        if percent <= 0:
            return Decimal("0")
        discount = reservation.base_rate * (percent / Decimal("100"))
        return discount * Decimal("-1")
    if amount_value is not None:
        discount = _parse_decimal(amount_value)
        if discount <= 0:
            return Decimal("0")
        return discount * Decimal("-1")
    return Decimal("0")


def _default_description(rule_type: PriceRuleType) -> str:
    mapping = {
        PriceRuleType.PEAK_DATE: "Peak date surcharge",
        PriceRuleType.LATE_CHECKOUT: "Late checkout fee",
        PriceRuleType.LODGING_SURCHARGE: "Lodging surcharge",
        PriceRuleType.VIP: "VIP discount",
    }
    return mapping.get(rule_type, rule_type.value)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_CURRENCY_QUANT, rounding=ROUND_HALF_UP)
