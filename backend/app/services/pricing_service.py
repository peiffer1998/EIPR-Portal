"""Pricing engine service for reservations."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    OwnerIcon,
    OwnerProfile,
    Pet,
    PetIcon,
    PriceRule,
    PriceRuleType,
    Promotion,
    PromotionKind,
    Reservation,
)

MONEY_PLACES = Decimal("0.01")


@dataclass(slots=True)
class PricingLine:
    """Individual component contributing to a reservation quote."""

    description: str
    amount: Decimal


@dataclass(slots=True)
class PricingQuote:
    """Aggregate pricing output for a reservation."""

    reservation_id: UUID
    items: list[PricingLine]
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal

    def to_dict(self) -> dict[str, Any]:
        """Serialize the quote to plain types for responses."""

        def _serialize(line: PricingLine) -> dict[str, str]:
            return {
                "description": line.description,
                "amount": _to_str(line.amount),
            }

        return {
            "reservation_id": str(self.reservation_id),
            "items": [_serialize(line) for line in self.items],
            "subtotal": _to_str(self.subtotal),
            "discount_total": _to_str(self.discount_total),
            "tax_total": _to_str(self.tax_total),
            "total": _to_str(self.total),
        }


def _to_money(value: Decimal | float | str) -> Decimal:
    return Decimal(value).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _to_str(value: Decimal) -> str:
    return f"{value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP):.2f}"


async def quote_reservation(
    session: AsyncSession,
    *,
    reservation_id: UUID,
    account_id: UUID,
    promotion_code: str | None = None,
) -> PricingQuote:
    """Produce a pricing quote for the given reservation."""

    reservation = await _load_reservation(session, reservation_id, account_id)
    if reservation is None:
        raise ValueError("Reservation not found for account")

    items: list[PricingLine] = [
        PricingLine(description="Base rate", amount=_to_money(reservation.base_rate))
    ]

    rules = await _list_active_rules(session, account_id)
    for rule in rules:
        items.extend(_apply_rule(rule, reservation))

    discount_total = Decimal("0.00")
    subtotal = sum((line.amount for line in items), Decimal("0.00"))

    if promotion_code:
        promotion = await _get_active_promotion(
            session,
            account_id=account_id,
            code=promotion_code,
            reference_date=reservation.start_at.date(),
        )
        if promotion is not None:
            promo_discount = _apply_promotion(promotion, subtotal)
            if promo_discount:
                discount_line = PricingLine(
                    description=f"Promotion {promotion.code}",
                    amount=-promo_discount,
                )
                items.append(discount_line)
                subtotal += discount_line.amount

    gross_subtotal = Decimal("0.00")
    for line in items:
        if line.amount < 0:
            discount_total += -line.amount
        else:
            gross_subtotal += line.amount

    subtotal = _to_money(gross_subtotal)
    discount_total = _to_money(discount_total)
    tax_total = Decimal("0.00")
    total = subtotal - discount_total + tax_total

    return PricingQuote(
        reservation_id=reservation.id,
        items=items,
        subtotal=subtotal,
        discount_total=discount_total,
        tax_total=tax_total,
        total=_to_money(total),
    )


async def _load_reservation(
    session: AsyncSession,
    reservation_id: UUID,
    account_id: UUID,
) -> Reservation | None:
    stmt: Select[tuple[Reservation]] = (
        select(Reservation)
        .options(
            selectinload(Reservation.pet)
            .selectinload(Pet.icon_assignments)
            .selectinload(PetIcon.icon),
            selectinload(Reservation.pet)
            .selectinload(Pet.owner)
            .selectinload(OwnerProfile.icon_assignments)
            .selectinload(OwnerIcon.icon),
        )
        .where(
            and_(
                Reservation.id == reservation_id,
                Reservation.account_id == account_id,
            )
        )
    )
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def _list_active_rules(
    session: AsyncSession, account_id: UUID
) -> list[PriceRule]:
    stmt = select(PriceRule).where(
        PriceRule.account_id == account_id, PriceRule.active.is_(True)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _get_active_promotion(
    session: AsyncSession,
    *,
    account_id: UUID,
    code: str,
    reference_date: datetime.date,
) -> Promotion | None:
    stmt = select(Promotion).where(
        Promotion.account_id == account_id,
        Promotion.code == code,
        Promotion.active.is_(True),
    )
    result = await session.execute(stmt)
    promotion = result.scalars().one_or_none()
    if promotion is None:
        return None

    if promotion.starts_on and reference_date < promotion.starts_on:
        return None
    if promotion.ends_on and reference_date > promotion.ends_on:
        return None
    return promotion


def _apply_promotion(promotion: Promotion, subtotal: Decimal) -> Decimal:
    if promotion.kind is PromotionKind.AMOUNT:
        return _to_money(min(subtotal, Decimal(promotion.value)))
    percent = Decimal(promotion.value) / Decimal("100")
    return _to_money(subtotal * percent)


def _apply_rule(rule: PriceRule, reservation: Reservation) -> list[PricingLine]:
    handler_map = {
        PriceRuleType.PEAK_DATE: _rule_peak_date,
        PriceRuleType.LATE_CHECKOUT: _rule_late_checkout,
        PriceRuleType.LODGING_SURCHARGE: _rule_lodging_surcharge,
        PriceRuleType.VIP: _rule_vip,
    }
    handler = handler_map.get(rule.rule_type)
    if handler is None:
        return []
    return handler(rule, reservation)


def _rule_peak_date(rule: PriceRule, reservation: Reservation) -> list[PricingLine]:
    params = rule.params or {}
    raw_dates = params.get("dates", [])
    if not raw_dates:
        return []

    stay_dates = list(_reservation_dates(reservation))
    if not any(date.isoformat() in raw_dates for date in stay_dates):
        return []

    lines: list[PricingLine] = []
    if (percent := params.get("percent")) is not None:
        amount = _to_money(reservation.base_rate) * _to_money(percent) / Decimal("100")
        lines.append(PricingLine("Peak date surcharge", amount.quantize(MONEY_PLACES)))
    if (flat := params.get("amount")) is not None:
        lines.append(PricingLine("Peak date surcharge", _to_money(flat)))
    return lines


def _rule_late_checkout(rule: PriceRule, reservation: Reservation) -> list[PricingLine]:
    params = rule.params or {}
    raw_amount = params.get("amount")
    if raw_amount is None:
        return []
    cutoff_time = params.get("hour")
    cutoff_str = params.get("time")
    checkout_at = reservation.check_out_at or reservation.end_at
    if checkout_at is None:
        return []
    threshold: datetime.time
    if cutoff_str:
        threshold = datetime.time.fromisoformat(cutoff_str)
    elif cutoff_time is not None:
        threshold = datetime.time(int(cutoff_time), 0)
    else:
        return []
    if checkout_at.timetz() <= threshold.replace(tzinfo=checkout_at.tzinfo):
        return []
    return [PricingLine("Late checkout fee", _to_money(raw_amount))]


def _rule_lodging_surcharge(
    rule: PriceRule, reservation: Reservation
) -> list[PricingLine]:
    params = rule.params or {}
    amount = params.get("amount")
    if amount is None:
        return []
    reservation_types: Iterable[str] = params.get("reservation_types", [])
    if (
        reservation_types
        and reservation.reservation_type.value not in reservation_types
    ):
        return []
    kennel_ids: Iterable[str] = params.get("kennel_ids", [])
    if kennel_ids and (
        reservation.kennel_id is None or str(reservation.kennel_id) not in kennel_ids
    ):
        return []
    return [PricingLine("Lodging surcharge", _to_money(amount))]


def _rule_vip(rule: PriceRule, reservation: Reservation) -> list[PricingLine]:
    params = rule.params or {}
    percent = params.get("percent")
    if percent is None:
        return []
    icon_slugs: set[str] = set(params.get("icon_slugs", ["vip"]))
    if _has_vip_icon(reservation, icon_slugs):
        discount = (
            _to_money(reservation.base_rate) * _to_money(percent) / Decimal("100")
        )
        return [PricingLine("VIP discount", -discount.quantize(MONEY_PLACES))]
    return []


def _reservation_dates(reservation: Reservation) -> Iterable[datetime.date]:
    start_date = reservation.start_at.date()
    end_date = reservation.end_at.date()
    current = start_date
    while current <= end_date:
        yield current
        current += datetime.timedelta(days=1)


def _has_vip_icon(reservation: Reservation, icon_slugs: set[str]) -> bool:
    pet_icons = {
        assignment.icon.slug
        for assignment in reservation.pet.icon_assignments
        if assignment.icon
    }
    owner_icons: set[str] = set()
    owner = reservation.pet.owner
    if owner is not None:
        owner_icons = {
            assignment.icon.slug
            for assignment in owner.icon_assignments
            if assignment.icon
        }
    return bool(pet_icons & icon_slugs or owner_icons & icon_slugs)
