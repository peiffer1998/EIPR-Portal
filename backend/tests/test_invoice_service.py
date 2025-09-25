"""Tests for invoice service totals and deposits."""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

import pytest

from app.db.session import get_sessionmaker
from app.models import (
    Account,
    DepositStatus,
    Invoice,
    Location,
    OwnerProfile,
    Pet,
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
from app.services import invoice_service

pytestmark = pytest.mark.asyncio


async def _seed_reservation(
    session, *, base_rate: Decimal = Decimal("200.00")
) -> tuple[Account, Reservation]:
    account = Account(name="Invoice Resort", slug=f"invoice-{uuid.uuid4().hex[:6]}")
    session.add(account)
    await session.flush()

    location = Location(account_id=account.id, name="Cedar Rapids", timezone="UTC")
    session.add(location)
    await session.flush()

    user = User(
        account_id=account.id,
        email=f"owner+{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="x",
        first_name="Casey",
        last_name="Client",
        role=UserRole.PET_PARENT,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    await session.flush()

    owner = OwnerProfile(user_id=user.id)
    session.add(owner)
    await session.flush()

    pet = Pet(owner_id=owner.id, name="InvoiceDog", pet_type=PetType.DOG)
    session.add(pet)
    await session.flush()

    start_at = datetime.datetime(2025, 5, 1, 10, tzinfo=datetime.timezone.utc)
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
    return account, reservation


async def test_create_invoice_from_reservation(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, reservation = await _seed_reservation(session)
        session.add(
            PriceRule(
                account_id=account.id,
                rule_type=PriceRuleType.PEAK_DATE,
                params={
                    "dates": [reservation.start_at.date().isoformat()],
                    "amount": "25.00",
                },
            )
        )
        await session.commit()

        invoice_id = await invoice_service.create_from_reservation(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
        )

        invoice = await session.get(Invoice, invoice_id)
        assert invoice is not None
        await session.refresh(invoice, attribute_names=["items"])
        assert invoice.subtotal == Decimal("225.00")
        assert invoice.discount_total == Decimal("0.00")
        assert invoice.total == Decimal("225.00")
        assert invoice.total_amount == invoice.total
        assert len(invoice.items) == 2  # base rate + surcharge


async def test_compute_totals_with_promotion(reset_database, db_url: str) -> None:
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
                Promotion(
                    account_id=account.id,
                    code="WELCOME10",
                    kind=PromotionKind.PERCENT,
                    value=Decimal("10"),
                    starts_on=reservation.start_at.date() - datetime.timedelta(days=1),
                    ends_on=reservation.start_at.date() + datetime.timedelta(days=5),
                    active=True,
                ),
            ]
        )
        await session.commit()

        invoice_id = await invoice_service.create_from_reservation(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
        )

        totals = await invoice_service.compute_totals(
            session,
            invoice_id=invoice_id,
            account_id=account.id,
            promotion_code="WELCOME10",
        )
        assert totals.subtotal == Decimal("220.00")
        assert totals.discount_total == Decimal("22.00")
        assert totals.total == Decimal("198.00")

        invoice = await session.get(Invoice, invoice_id)
        assert invoice is not None
        assert invoice.total == Decimal("198.00")


async def test_deposit_lifecycle(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, reservation = await _seed_reservation(session)

        held = await invoice_service.settle_deposit(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
            action="hold",
            amount=Decimal("50.00"),
        )
        assert held.status is DepositStatus.HELD
        assert held.amount == Decimal("50.00")

        consumed = await invoice_service.settle_deposit(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
            action="consume",
            amount=Decimal("50.00"),
        )
        assert consumed.status is DepositStatus.CONSUMED

        # Hold again for a refund flow
        await invoice_service.settle_deposit(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
            action="hold",
            amount=Decimal("30.00"),
        )
        refunded = await invoice_service.settle_deposit(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
            action="refund",
            amount=Decimal("30.00"),
        )
        assert refunded.status is DepositStatus.REFUNDED

        # Hold again for forfeit
        await invoice_service.settle_deposit(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
            action="hold",
            amount=Decimal("40.00"),
        )
        forfeited = await invoice_service.settle_deposit(
            session,
            reservation_id=reservation.id,
            account_id=account.id,
            action="forfeit",
            amount=Decimal("40.00"),
        )
        assert forfeited.status is DepositStatus.FORFEITED

        # Attempting to settle without hold should fail
        with pytest.raises(ValueError):
            await invoice_service.settle_deposit(
                session,
                reservation_id=reservation.id,
                account_id=account.id,
                action="consume",
                amount=Decimal("10.00"),
            )
