"""Tests for grooming booking workflow."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import (
    Account,
    CommissionType,
    GroomingAddon,
    GroomingAppointmentStatus,
    GroomingService,
    CommissionPayout,
    Invoice,
    Location,
    OwnerProfile,
    Pet,
    PetType,
    Reservation,
    ReservationStatus,
    ReservationType,
    Specialist,
    SpecialistSchedule,
    User,
    UserRole,
    UserStatus,
)
from app.services import commission_service
from app.services.grooming_booking_service import (
    book_appointment,
    cancel_appointment,
    compute_commission_amount,
    reschedule_appointment,
    update_status,
)


@pytest_asyncio.fixture()
async def grooming_setup(reset_database: None) -> dict[str, uuid.UUID]:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        account = Account(name="EIPR", slug="eipr")
        session.add(account)
        await session.flush()

        location = Location(account_id=account.id, name="Cedar", timezone="UTC")
        session.add(location)
        await session.flush()

        staff_user = User(
            account_id=account.id,
            email="groomer@example.com",
            hashed_password=get_password_hash("Groomer1!"),
            first_name="Jamie",
            last_name="Trim",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
        )
        session.add(staff_user)
        await session.flush()

        owner_user = User(
            account_id=account.id,
            email="owner@example.com",
            hashed_password=get_password_hash("Owner1!"),
            first_name="Taylor",
            last_name="Owner",
            role=UserRole.PET_PARENT,
            status=UserStatus.ACTIVE,
        )
        session.add(owner_user)
        await session.flush()

        owner = OwnerProfile(user_id=owner_user.id)
        session.add(owner)
        await session.flush()

        pet = Pet(
            owner_id=owner.id,
            name="Scout",
            pet_type=PetType.DOG,
        )
        session.add(pet)
        await session.flush()

        specialist = Specialist(
            account_id=account.id,
            location_id=location.id,
            name="Pat Stylist",
            user_id=staff_user.id,
            commission_type=CommissionType.PERCENT,
            commission_rate=Decimal("12.50"),
        )
        session.add(specialist)
        await session.flush()

        schedule = SpecialistSchedule(
            account_id=account.id,
            specialist_id=specialist.id,
            weekday=0,
            start_time=datetime(2025, 1, 6, 9, 0).time(),
            end_time=datetime(2025, 1, 6, 17, 0).time(),
        )
        session.add(schedule)

        service = GroomingService(
            account_id=account.id,
            code="FULL",
            name="Full Groom",
            base_duration_minutes=60,
            base_price=Decimal("85.00"),
        )
        session.add(service)
        await session.flush()

        addon = GroomingAddon(
            account_id=account.id,
            code="TEETH",
            name="Teeth Brushing",
            add_duration_minutes=15,
            add_price=Decimal("20.00"),
        )
        session.add(addon)
        await session.flush()

        reservation = Reservation(
            account_id=account.id,
            location_id=location.id,
            pet_id=pet.id,
            reservation_type=ReservationType.GROOMING,
            status=ReservationStatus.CONFIRMED,
            start_at=datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
            end_at=datetime(2025, 1, 6, 10, 30, tzinfo=UTC),
            base_rate=Decimal("0"),
        )
        session.add(reservation)
        await session.commit()

        return {
            "account_id": account.id,
            "location_id": location.id,
            "owner_id": owner.id,
            "pet_id": pet.id,
            "specialist_id": specialist.id,
            "service_id": service.id,
            "addon_id": addon.id,
            "reservation_id": reservation.id,
        }


@pytest.mark.asyncio
async def test_book_appointment_creates_invoice_and_commission(
    grooming_setup: dict[str, uuid.UUID],
) -> None:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        appointment = await book_appointment(
            session,
            account_id=grooming_setup["account_id"],
            owner_id=grooming_setup["owner_id"],
            pet_id=grooming_setup["pet_id"],
            specialist_id=grooming_setup["specialist_id"],
            service_id=grooming_setup["service_id"],
            addon_ids=[grooming_setup["addon_id"]],
            start_at=datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
            notes="Full spa",
            reservation_id=grooming_setup["reservation_id"],
        )

        assert appointment.price_snapshot == Decimal("105.00")
        assert appointment.commission_amount == Decimal("13.13")
        assert appointment.invoice_id is not None

        invoice = await session.get(
            Invoice,
            appointment.invoice_id,
            options=[selectinload(Invoice.items)],
        )
        assert invoice is not None
        assert len(invoice.items) == 2
    assert invoice.total == Decimal("105.00")


@pytest.mark.asyncio
async def test_commission_build_uses_specialist_location(
    grooming_setup: dict[str, uuid.UUID],
) -> None:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        appointment = await book_appointment(
            session,
            account_id=grooming_setup["account_id"],
            owner_id=grooming_setup["owner_id"],
            pet_id=grooming_setup["pet_id"],
            specialist_id=grooming_setup["specialist_id"],
            service_id=grooming_setup["service_id"],
            addon_ids=[],
            start_at=datetime(2025, 1, 6, 11, 0, tzinfo=UTC),
            notes="Commission test",
            reservation_id=grooming_setup["reservation_id"],
        )

        appointment.status = GroomingAppointmentStatus.COMPLETED
        await session.commit()

        created = await commission_service.build_from_completed_appointments(
            session,
            account_id=grooming_setup["account_id"],
            date_from=appointment.start_at.date(),
            date_to=appointment.start_at.date(),
        )
        assert created == 1

        payout_row = await session.execute(
            select(CommissionPayout).where(
                CommissionPayout.appointment_id == appointment.id
            )
        )
        payout = payout_row.scalar_one()
        assert payout.location_id == grooming_setup["location_id"]


@pytest.mark.asyncio
async def test_reschedule_enforces_overlap(
    grooming_setup: dict[str, uuid.UUID],
) -> None:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        await book_appointment(
            session,
            account_id=grooming_setup["account_id"],
            owner_id=grooming_setup["owner_id"],
            pet_id=grooming_setup["pet_id"],
            specialist_id=grooming_setup["specialist_id"],
            service_id=grooming_setup["service_id"],
            addon_ids=[],
            start_at=datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
            reservation_id=None,
        )
        second = await book_appointment(
            session,
            account_id=grooming_setup["account_id"],
            owner_id=grooming_setup["owner_id"],
            pet_id=grooming_setup["pet_id"],
            specialist_id=grooming_setup["specialist_id"],
            service_id=grooming_setup["service_id"],
            addon_ids=[],
            start_at=datetime(2025, 1, 6, 11, 0, tzinfo=UTC),
            reservation_id=None,
        )

        with pytest.raises(ValueError):
            await reschedule_appointment(
                session,
                account_id=grooming_setup["account_id"],
                appointment_id=second.id,
                new_start_at=datetime(2025, 1, 6, 9, 30, tzinfo=UTC),
            )

        updated = await reschedule_appointment(
            session,
            account_id=grooming_setup["account_id"],
            appointment_id=second.id,
            new_start_at=datetime(2025, 1, 6, 13, 0, tzinfo=UTC),
        )
        assert updated.start_at.replace(tzinfo=UTC) == datetime(
            2025, 1, 6, 13, 0, tzinfo=UTC
        )
        assert updated.end_at.replace(tzinfo=UTC) == datetime(
            2025, 1, 6, 14, 0, tzinfo=UTC
        )


@pytest.mark.asyncio
async def test_cancel_and_status_transitions(
    grooming_setup: dict[str, uuid.UUID],
) -> None:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        appointment = await book_appointment(
            session,
            account_id=grooming_setup["account_id"],
            owner_id=grooming_setup["owner_id"],
            pet_id=grooming_setup["pet_id"],
            specialist_id=grooming_setup["specialist_id"],
            service_id=grooming_setup["service_id"],
            addon_ids=[],
            start_at=datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
            reservation_id=None,
        )

        checked_in = await update_status(
            session,
            account_id=grooming_setup["account_id"],
            appointment_id=appointment.id,
            new_status=GroomingAppointmentStatus.CHECKED_IN,
        )
        assert checked_in.status is GroomingAppointmentStatus.CHECKED_IN

        in_progress = await update_status(
            session,
            account_id=grooming_setup["account_id"],
            appointment_id=appointment.id,
            new_status=GroomingAppointmentStatus.IN_PROGRESS,
        )
        assert in_progress.status is GroomingAppointmentStatus.IN_PROGRESS

        completed = await update_status(
            session,
            account_id=grooming_setup["account_id"],
            appointment_id=appointment.id,
            new_status=GroomingAppointmentStatus.COMPLETED,
        )
        assert completed.status is GroomingAppointmentStatus.COMPLETED

        with pytest.raises(ValueError):
            await update_status(
                session,
                account_id=grooming_setup["account_id"],
                appointment_id=appointment.id,
                new_status=GroomingAppointmentStatus.SCHEDULED,
            )

        another = await book_appointment(
            session,
            account_id=grooming_setup["account_id"],
            owner_id=grooming_setup["owner_id"],
            pet_id=grooming_setup["pet_id"],
            specialist_id=grooming_setup["specialist_id"],
            service_id=grooming_setup["service_id"],
            addon_ids=[],
            start_at=datetime(2025, 1, 6, 14, 0, tzinfo=UTC),
            reservation_id=None,
        )
        canceled = await cancel_appointment(
            session,
            account_id=grooming_setup["account_id"],
            appointment_id=another.id,
            reason="Pet became ill",
        )
        assert canceled.status is GroomingAppointmentStatus.CANCELED
        assert "Pet became ill" in (canceled.notes or "")


def test_compute_commission_amount() -> None:
    assert compute_commission_amount(
        Decimal("100"), CommissionType.PERCENT, Decimal("10")
    ) == Decimal("10.00")
    assert compute_commission_amount(
        Decimal("100"), CommissionType.AMOUNT, Decimal("25")
    ) == Decimal("25.00")
    assert compute_commission_amount(Decimal("100"), None, Decimal("25")) is None
