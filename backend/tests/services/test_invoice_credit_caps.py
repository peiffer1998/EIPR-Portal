"""Tests ensuring invoice credit applications respect caps."""

from __future__ import annotations

from decimal import Decimal
import datetime
import uuid

import pytest

from app.db.session import get_sessionmaker
from app.models import (
    Account,
    Invoice,
    Location,
    OwnerProfile,
    PackageApplicationType,
    PackageType,
    Pet,
    PetType,
    Reservation,
    ReservationStatus,
    ReservationType,
    StoreCreditSource,
    User,
    UserRole,
    UserStatus,
)
from app.services import (
    invoice_service,
    packages_service,
    store_credit_service,
)

pytestmark = pytest.mark.asyncio


async def _seed_account(session):
    account = Account(name="Caps Resort", slug=f"caps-{uuid.uuid4().hex[:6]}")
    session.add(account)
    await session.flush()

    location = Location(account_id=account.id, name="Marion", timezone="UTC")
    session.add(location)
    await session.flush()

    user = User(
        account_id=account.id,
        email=f"caps+{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="x",
        first_name="Casey",
        last_name="Caps",
        role=UserRole.PET_PARENT,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    await session.flush()

    owner = OwnerProfile(user_id=user.id)
    session.add(owner)
    await session.flush()

    pet = Pet(owner_id=owner.id, name="CapDog", pet_type=PetType.DOG)
    session.add(pet)
    await session.commit()

    return account, location, owner, pet


async def _make_invoice(
    session,
    account,
    location,
    pet,
    amount: Decimal,
    reservation_type: ReservationType = ReservationType.BOARDING,
) -> uuid.UUID:
    start_at = datetime.datetime(2025, 3, 1, 8, tzinfo=datetime.timezone.utc)
    end_at = start_at + datetime.timedelta(days=1)
    reservation = Reservation(
        account_id=account.id,
        location_id=location.id,
        pet_id=pet.id,
        reservation_type=reservation_type,
        status=ReservationStatus.CONFIRMED,
        start_at=start_at,
        end_at=end_at,
        base_rate=amount,
    )
    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)
    return await invoice_service.create_from_reservation(
        session,
        reservation_id=reservation.id,
        account_id=account.id,
    )


async def test_package_credit_caps_invoice_total(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, location, owner, pet = await _seed_account(session)

        package_type = PackageType(
            account_id=account.id,
            name="Mega Daycare",
            applies_to=PackageApplicationType.DAYCARE,
            credits_per_package=10,
            price=Decimal("500.00"),
            active=True,
        )
        session.add(package_type)
        await session.commit()

        await packages_service.purchase_package(
            session,
            owner_id=owner.id,
            package_type_id=package_type.id,
            quantity=1,
        )

        invoice_id = await _make_invoice(
            session,
            account=account,
            location=location,
            pet=pet,
            amount=Decimal("120.00"),
            reservation_type=ReservationType.DAYCARE,
        )
        summary = await packages_service.apply_package_credits(
            session,
            invoice_id=invoice_id,
            account_id=account.id,
        )
        invoice = await session.get(Invoice, invoice_id)
        assert invoice is not None
        assert invoice.credits_total <= invoice.total
        assert invoice.total_amount == invoice.total - invoice.credits_total
        assert summary.applied_amount == invoice.credits_total


async def test_store_credit_caps_balance_and_total(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, location, owner, pet = await _seed_account(session)

        await store_credit_service.add_credit(
            session,
            account_id=account.id,
            owner_id=owner.id,
            amount=Decimal("50.00"),
            source=StoreCreditSource.MANUAL,
            note="Goodwill",
        )

        invoice_id = await _make_invoice(
            session,
            account=account,
            location=location,
            pet=pet,
            amount=Decimal("80.00"),
        )
        applied = await store_credit_service.apply_store_credit(
            session,
            invoice_id=invoice_id,
            account_id=account.id,
            owner_id=owner.id,
            amount=Decimal("120.00"),
        )
        assert applied == Decimal("50.00")
        invoice = await session.get(Invoice, invoice_id)
        assert invoice is not None
        assert invoice.credits_total == Decimal("50.00")
        assert invoice.total_amount == Decimal("30.00")

        with pytest.raises(ValueError):
            await store_credit_service.apply_store_credit(
                session,
                invoice_id=invoice_id,
                account_id=account.id,
                owner_id=owner.id,
                amount=Decimal("50.00"),
            )
