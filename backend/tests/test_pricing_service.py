"""Unit tests for the pricing service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.db.session import get_sessionmaker
from app.models import (
    Account,
    Location,
    OwnerProfile,
    Pet,
    PetType,
    PriceRule,
    PriceRuleType,
    Reservation,
    ReservationType,
    User,
    UserRole,
    UserStatus,
)
from app.services import pricing_service

pytestmark = pytest.mark.asyncio


async def _seed_reservation(
    db_url: str, base_rate: Decimal = Decimal("100.00")
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create an account, owner, pet, and reservation."""
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account = Account(name="Pricing Resort", slug="pricing-resort")
        session.add(account)
        await session.flush()

        location = Location(account_id=account.id, name="Pricing", timezone="UTC")
        session.add(location)
        await session.flush()

        user = User(
            account_id=account.id,
            email="owner@example.com",
            hashed_password="hashed",
            first_name="Olive",
            last_name="Owner",
            role=UserRole.PET_PARENT,
            status=UserStatus.ACTIVE,
        )
        session.add(user)
        await session.flush()

        owner = OwnerProfile(user_id=user.id)
        session.add(owner)
        await session.flush()

        pet = Pet(
            owner_id=owner.id,
            home_location_id=location.id,
            name="PricedPet",
            pet_type=PetType.DOG,
        )
        session.add(pet)
        await session.flush()

        start_at = datetime.now(timezone.utc) + timedelta(days=5)
        end_at = start_at + timedelta(days=3)
        reservation = Reservation(
            account_id=account.id,
            location_id=location.id,
            pet_id=pet.id,
            reservation_type=ReservationType.BOARDING,
            start_at=start_at,
            end_at=end_at,
            base_rate=base_rate,
        )
        session.add(reservation)
        await session.commit()
        return account.id, reservation.id


async def test_quote_with_peak_date_rule(reset_database, db_url):
    account_id, reservation_id = await _seed_reservation(db_url)
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        rule = PriceRule(
            account_id=account_id,
            rule_type=PriceRuleType.PEAK_DATE,
            params={
                "start_date": datetime.now(timezone.utc).date().isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=10))
                .date()
                .isoformat(),
                "amount": "25.00",
            },
        )
        session.add(rule)
        await session.commit()

        quote = await pricing_service.quote_reservation(
            session, reservation_id=reservation_id
        )
        assert quote.total == Decimal("125.00")
        assert any(line.rule_type == PriceRuleType.PEAK_DATE for line in quote.lines)


async def test_quote_with_late_checkout_fee(reset_database, db_url):
    account_id, reservation_id = await _seed_reservation(db_url)
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        rule = PriceRule(
            account_id=account_id,
            rule_type=PriceRuleType.LATE_CHECKOUT,
            params={"after_hour": 15, "amount": "30.00"},
        )
        session.add(rule)
        await session.commit()

        quote = await pricing_service.quote_reservation(
            session, reservation_id=reservation_id
        )
        assert quote.total == Decimal("130.00")
        assert any(
            line.rule_type == PriceRuleType.LATE_CHECKOUT for line in quote.lines
        )


async def test_quote_with_lodging_surcharge(reset_database, db_url):
    account_id, reservation_id = await _seed_reservation(db_url, Decimal("200.00"))
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        rule = PriceRule(
            account_id=account_id,
            rule_type=PriceRuleType.LODGING_SURCHARGE,
            params={"percent": "10"},
        )
        session.add(rule)
        await session.commit()

        quote = await pricing_service.quote_reservation(
            session, reservation_id=reservation_id
        )
        assert quote.total == Decimal("220.00")
        assert any(line.description == "Lodging surcharge" for line in quote.lines)


async def test_quote_with_vip_discount(reset_database, db_url):
    account_id, reservation_id = await _seed_reservation(db_url, Decimal("150.00"))
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        rule = PriceRule(
            account_id=account_id,
            rule_type=PriceRuleType.VIP,
            params={"percent": "10"},
        )
        session.add(rule)
        await session.commit()

        quote = await pricing_service.quote_reservation(
            session, reservation_id=reservation_id
        )
        assert quote.total == Decimal("135.00")
        assert quote.discount_total == Decimal("15.00")


async def test_quote_combined_rules(reset_database, db_url):
    account_id, reservation_id = await _seed_reservation(db_url, Decimal("250.00"))
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        session.add_all(
            [
                PriceRule(
                    account_id=account_id,
                    rule_type=PriceRuleType.PEAK_DATE,
                    params={
                        "start_date": datetime.now(timezone.utc).date().isoformat(),
                        "end_date": (datetime.now(timezone.utc) + timedelta(days=7))
                        .date()
                        .isoformat(),
                        "amount": "20.00",
                    },
                ),
                PriceRule(
                    account_id=account_id,
                    rule_type=PriceRuleType.LATE_CHECKOUT,
                    params={"after_hour": 12, "amount": "15.00"},
                ),
                PriceRule(
                    account_id=account_id,
                    rule_type=PriceRuleType.VIP,
                    params={"percent": "5"},
                ),
            ]
        )
        await session.commit()

        quote = await pricing_service.quote_reservation(
            session, reservation_id=reservation_id
        )
        assert quote.total == Decimal("275.00")
        assert len(quote.lines) == 4
        assert quote.discount_total == Decimal("12.50")
