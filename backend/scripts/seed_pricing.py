"""Seed baseline pricing rules and promotions."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models import Account, PriceRule, PriceRuleType, Promotion, PromotionKind

PEAK_LABEL = "seed_default_peak"
LATE_CHECKOUT_LABEL = "seed_default_late_checkout"
SURCHARGE_LABEL = "seed_default_lodging"
PROMO_CODE = "WELCOME10"


def _next_holiday(today: date | None = None) -> date:
    today = today or date.today()
    holiday_candidates = [
        date(today.year, 7, 4),
        date(today.year, 11, 28),
        date(today.year, 12, 25),
    ]
    for candidate in holiday_candidates:
        if candidate >= today:
            return candidate
    return holiday_candidates[0].replace(year=today.year + 1)


async def seed_pricing() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        accounts = (await session.execute(select(Account))).scalars().all()
        if not accounts:
            print("No accounts found; nothing to seed.")
            return

        holiday = _next_holiday()
        rules_created = 0
        promos_created = 0

        for account in accounts:
            existing_rules = (
                (
                    await session.execute(
                        select(PriceRule).where(PriceRule.account_id == account.id)
                    )
                )
                .scalars()
                .all()
            )

            def _has_label(label: str) -> bool:
                return any(
                    rule.params.get("seed_label") == label for rule in existing_rules
                )

            if not _has_label(PEAK_LABEL):
                session.add(
                    PriceRule(
                        account_id=account.id,
                        rule_type=PriceRuleType.PEAK_DATE,
                        params={
                            "seed_label": PEAK_LABEL,
                            "dates": [holiday.isoformat()],
                            "amount": "25.00",
                        },
                    )
                )
                rules_created += 1

            if not _has_label(LATE_CHECKOUT_LABEL):
                session.add(
                    PriceRule(
                        account_id=account.id,
                        rule_type=PriceRuleType.LATE_CHECKOUT,
                        params={
                            "seed_label": LATE_CHECKOUT_LABEL,
                            "hour": 11,
                            "amount": "15.00",
                        },
                    )
                )
                rules_created += 1

            if not _has_label(SURCHARGE_LABEL):
                session.add(
                    PriceRule(
                        account_id=account.id,
                        rule_type=PriceRuleType.LODGING_SURCHARGE,
                        params={
                            "seed_label": SURCHARGE_LABEL,
                            "reservation_types": ["boarding"],
                            "amount": "35.00",
                        },
                    )
                )
                rules_created += 1

            promo_exists = (
                await session.execute(
                    select(Promotion).where(
                        Promotion.account_id == account.id,
                        Promotion.code == PROMO_CODE,
                    )
                )
            ).scalar_one_or_none()

            if promo_exists is None:
                session.add(
                    Promotion(
                        account_id=account.id,
                        code=PROMO_CODE,
                        kind=PromotionKind.PERCENT,
                        value=Decimal("10"),
                        starts_on=date.today(),
                        ends_on=date.today() + timedelta(days=365),
                        active=True,
                    )
                )
                promos_created += 1

        if rules_created or promos_created:
            await session.commit()

        print(
            f"Seeded {rules_created} pricing rule(s) and {promos_created} promotion(s)."
        )


async def _seed_async() -> None:
    await seed_pricing()


def main() -> None:
    asyncio.run(_seed_async())


if __name__ == "__main__":
    main()
