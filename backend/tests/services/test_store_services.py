"""Service-level tests for store packages, gift certificates, and credits."""

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
    ReservationType,
    ReservationStatus,
    User,
    UserRole,
    UserStatus,
)
from app.services import (
    gift_cert_service,
    invoice_service,
    packages_service,
    store_credit_service,
)

pytestmark = pytest.mark.asyncio


async def _seed_owner(session) -> tuple[Account, Location, User, OwnerProfile, Pet]:
    account = Account(name="Store Resort", slug=f"store-{uuid.uuid4().hex[:6]}")
    session.add(account)
    await session.flush()

    location = Location(account_id=account.id, name="Coralville", timezone="UTC")
    session.add(location)
    await session.flush()

    user = User(
        account_id=account.id,
        email=f"owner+{uuid.uuid4().hex[:6]}@example.com",
        hashed_password="x",
        first_name="Olivia",
        last_name="Owner",
        role=UserRole.PET_PARENT,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    await session.flush()

    owner = OwnerProfile(user_id=user.id)
    session.add(owner)
    await session.flush()

    pet = Pet(owner_id=owner.id, name="StoreDog", pet_type=PetType.DOG)
    session.add(pet)
    await session.commit()
    await session.refresh(owner)
    await session.refresh(pet)

    return account, location, user, owner, pet


async def _create_reservation_with_invoice(
    session,
    *,
    account: Account,
    location: Location,
    pet: Pet,
    start_rate: Decimal,
    reservation_type: ReservationType = ReservationType.BOARDING,
) -> tuple[Reservation, uuid.UUID]:
    start_at = datetime.datetime(2025, 1, 1, 9, tzinfo=datetime.timezone.utc)
    end_at = start_at + datetime.timedelta(days=1)
    reservation = Reservation(
        account_id=account.id,
        location_id=location.id,
        pet_id=pet.id,
        reservation_type=reservation_type,
        status=ReservationStatus.CONFIRMED,
        start_at=start_at,
        end_at=end_at,
        base_rate=start_rate,
    )
    session.add(reservation)
    await session.commit()
    await session.refresh(reservation)

    invoice_id = await invoice_service.create_from_reservation(
        session,
        reservation_id=reservation.id,
        account_id=account.id,
    )
    return reservation, invoice_id


async def test_package_purchase_and_application(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, location, _, owner, pet = await _seed_owner(session)

        package_type = PackageType(
            account_id=account.id,
            name="Daycare 5-Pack",
            applies_to=PackageApplicationType.DAYCARE,
            credits_per_package=5,
            price=Decimal("150.00"),
            active=True,
        )
        session.add(package_type)
        await session.commit()

        invoice_id = await packages_service.purchase_package(
            session,
            owner_id=owner.id,
            package_type_id=package_type.id,
            quantity=1,
        )
        invoice = await session.get(Invoice, invoice_id)
        assert invoice is not None
        assert invoice.total == Decimal("150.00")
        assert invoice.credits_total == Decimal("0.00")

        reservation, invoice_to_apply_id = await _create_reservation_with_invoice(
            session,
            account=account,
            location=location,
            pet=pet,
            start_rate=Decimal("120.00"),
            reservation_type=ReservationType.DAYCARE,
        )
        summary = await packages_service.apply_package_credits(
            session,
            invoice_id=invoice_to_apply_id,
            account_id=account.id,
        )
        assert summary.applied_amount > Decimal("0")
        updated_invoice = await session.get(Invoice, invoice_to_apply_id)
        assert updated_invoice is not None
        assert updated_invoice.credits_total == summary.applied_amount
        assert (
            updated_invoice.total_amount
            == updated_invoice.total - summary.applied_amount
        )
        assert updated_invoice.total_amount >= Decimal("0.00")


async def test_gift_certificate_redeem_and_store_credit(
    reset_database, db_url: str
) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account, location, _, owner, pet = await _seed_owner(session)

        invoice_id, certificate = await gift_cert_service.purchase_gift_certificate(
            session,
            account_id=account.id,
            purchaser_owner_id=owner.id,
            amount=Decimal("75.00"),
        )
        assert certificate.remaining_value == Decimal("75.00")
        invoice = await session.get(Invoice, invoice_id)
        assert invoice is not None
        assert invoice.total == Decimal("75.00")

        balance_before = await store_credit_service.owner_balance(
            session,
            account_id=account.id,
            owner_id=owner.id,
        )
        assert balance_before == Decimal("0.00")

        await gift_cert_service.redeem_gift_certificate(
            session,
            code=certificate.code,
            account_id=account.id,
            owner_id=owner.id,
        )
        balance_after = await store_credit_service.owner_balance(
            session,
            account_id=account.id,
            owner_id=owner.id,
        )
        assert balance_after == Decimal("75.00")

        reservation, invoice_to_apply_id = await _create_reservation_with_invoice(
            session,
            account=account,
            location=location,
            pet=pet,
            start_rate=Decimal("60.00"),
        )
        applied = await store_credit_service.apply_store_credit(
            session,
            invoice_id=invoice_to_apply_id,
            account_id=account.id,
            owner_id=owner.id,
            amount=Decimal("90.00"),
        )
        assert applied == Decimal("60.00")
        new_balance = await store_credit_service.owner_balance(
            session,
            account_id=account.id,
            owner_id=owner.id,
        )
        assert new_balance == Decimal("15.00")
        updated_invoice = await session.get(Invoice, invoice_to_apply_id)
        assert updated_invoice is not None
        assert updated_invoice.credits_total == Decimal("60.00")
        assert updated_invoice.total_amount == Decimal("0.00")
