"""Tests for the pricing service."""

from __future__ import annotations

import datetime
from decimal import Decimal
import uuid

import pytest

from app.db.session import get_sessionmaker
from app.models import (
    Account,
    Icon,
    IconEntity,
    OwnerProfile,
    Pet,
    PetIcon,
    PetType,
    PriceRule,
    PriceRuleType,
    Promotion,
    PromotionKind,
    Reservation,
    ReservationType,
    User,
    UserRole,
    UserStatus,
)
from app.services import pricing_service

pytestmark = pytest.mark.asyncio


async def _seed_reservation(
    session, *, base_rate: Decimal = Decimal("100.00")
) -> tuple[Account, Reservation]:
    from app.models.location import Location

    account = Account(name="Pricing Resort", slug=f"pricing-{uuid.uuid4().hex[:6]}")
    session.add(account)
    await session.flush()

    location = Location(account_id=account.id, name="Cedar Rapids", timezone="UTC")
    session.add(location)
    await session.flush()

    user = User(
        account_id=account.id,
        email=f"parent+{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="x",
        first_name="Taylor",
        last_name="Parent",
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
        name="Scout",
        pet_type=PetType.DOG,
    )
    session.add(pet)
    await session.flush()

    start_at = datetime.datetime(2025, 5, 1, 12, tzinfo=datetime.timezone.utc)
    end_at = start_at + datetime.timedelta(days=2)

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
    await session.refresh(reservation)
    await session.refresh(reservation.pet)
    await session.refresh(reservation.pet.owner)
    return account, reservation


async def test_peak_date_rule_applies(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, reservation = await _seed_reservation(session)
        rule = PriceRule(
            account_id=account.id,
            rule_type=PriceRuleType.PEAK_DATE,
            params={
                "dates": [reservation.start_at.date().isoformat()],
                "amount": "25.00",
            },
        )
        session.add(rule)
        await session.commit()

        quote = await pricing_service.quote_reservation(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
        )
        data = quote.to_dict()
        assert any(
            item["description"] == "Peak date surcharge" and item["amount"] == "25.00"
            for item in data["items"]
        )
        assert data["total"] == "125.00"


async def test_late_checkout_rule(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, reservation = await _seed_reservation(session)
        reservation.check_out_at = reservation.end_at + datetime.timedelta(hours=5)
        await session.commit()

        session.add(
            PriceRule(
                account_id=account.id,
                rule_type=PriceRuleType.LATE_CHECKOUT,
                params={"hour": 11, "amount": "30.00"},
            )
        )
        await session.commit()

        quote = await pricing_service.quote_reservation(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
        )
        data = quote.to_dict()
        assert any(
            item["description"] == "Late checkout fee" and item["amount"] == "30.00"
            for item in data["items"]
        )
        assert data["total"] == "130.00"


async def test_vip_discount(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, reservation = await _seed_reservation(session)

        vip_icon = Icon(
            account_id=account.id,
            name="VIP",
            slug="vip",
            applies_to=IconEntity.PET,
        )
        session.add(vip_icon)
        await session.flush()

        session.add(
            PetIcon(
                account_id=account.id,
                pet_id=reservation.pet_id,
                icon_id=vip_icon.id,
            )
        )
        session.add(
            PriceRule(
                account_id=account.id,
                rule_type=PriceRuleType.VIP,
                params={"percent": "10"},
            )
        )
        await session.commit()

        quote = await pricing_service.quote_reservation(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
        )
        data = quote.to_dict()
        assert any(
            item["description"] == "VIP discount" and item["amount"] == "-10.00"
            for item in data["items"]
        )
        assert data["total"] == "90.00"
        assert data["discount_total"] == "10.00"


async def test_combined_rules_with_promotion(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, reservation = await _seed_reservation(session)
        session.add_all(
            [
                PriceRule(
                    account_id=account.id,
                    rule_type=PriceRuleType.PEAK_DATE,
                    params={
                        "dates": [reservation.start_at.date().isoformat()],
                        "amount": "20.00",
                    },
                ),
                PriceRule(
                    account_id=account.id,
                    rule_type=PriceRuleType.LATE_CHECKOUT,
                    params={"hour": 10, "amount": "15.00"},
                ),
            ]
        )
        session.add(
            Promotion(
                account_id=account.id,
                code="SPRING10",
                kind=PromotionKind.PERCENT,
                value=Decimal("10"),
                starts_on=reservation.start_at.date() - datetime.timedelta(days=1),
                ends_on=reservation.start_at.date() + datetime.timedelta(days=10),
                active=True,
            )
        )
        await session.commit()

        quote = await pricing_service.quote_reservation(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
            promotion_code="SPRING10",
        )
        data = quote.to_dict()
        assert data["subtotal"] == "135.00"
        assert data["discount_total"] == "13.50"
        assert data["total"] == "121.50"
        assert any(
            item["description"] == "Promotion SPRING10" for item in data["items"]
        )
