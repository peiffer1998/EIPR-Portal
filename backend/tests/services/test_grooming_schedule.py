"""Tests for grooming availability calculations."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest
import pytest_asyncio

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import (
    Account,
    CommissionType,
    GroomingAddon,
    GroomingAppointment,
    GroomingAppointmentStatus,
    GroomingService,
    Location,
    OwnerProfile,
    Pet,
    PetType,
    Specialist,
    SpecialistSchedule,
    SpecialistTimeOff,
    User,
    UserRole,
    UserStatus,
)
from app.services.grooming_schedule_service import AvailableSlot, list_available_slots

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture()
async def setup_account(reset_database: None) -> dict[str, uuid.UUID]:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        account = Account(name="Grooming Co", slug="grooming-co")
        session.add(account)
        await session.flush()

        location = Location(account_id=account.id, name="Main", timezone="UTC")
        session.add(location)
        await session.flush()

        staff_user = User(
            account_id=account.id,
            email="stylist@example.com",
            hashed_password=get_password_hash("Styl1st!"),
            first_name="Alex",
            last_name="Stylist",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
        )
        session.add(staff_user)
        await session.flush()

        owner_user = User(
            account_id=account.id,
            email="pet.parent@example.com",
            hashed_password=get_password_hash("Owner123!"),
            first_name="Robin",
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
            name="Bailey",
            pet_type=PetType.DOG,
        )
        session.add(pet)
        await session.flush()

        specialist = Specialist(
            account_id=account.id,
            location_id=location.id,
            name="Casey Groomer",
            user_id=staff_user.id,
            commission_type=CommissionType.PERCENT,
            commission_rate=Decimal("10.00"),
            active=True,
        )
        session.add(specialist)
        await session.flush()

        schedule = SpecialistSchedule(
            account_id=account.id,
            specialist_id=specialist.id,
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        session.add(schedule)

        service = GroomingService(
            account_id=account.id,
            code="BATH",
            name="Bath",
            base_duration_minutes=45,
            base_price=Decimal("65.00"),
        )
        session.add(service)
        await session.flush()

        addon = GroomingAddon(
            account_id=account.id,
            code="NAILS",
            name="Nail Trim",
            add_duration_minutes=15,
            add_price=Decimal("15.00"),
        )
        session.add(addon)
        await session.flush()

        time_off = SpecialistTimeOff(
            account_id=account.id,
            specialist_id=specialist.id,
            starts_at=datetime(2025, 1, 6, 10, 30, tzinfo=UTC),
            ends_at=datetime(2025, 1, 6, 11, 0, tzinfo=UTC),
            reason="Break",
        )
        session.add(time_off)

        appointment = GroomingAppointment(
            account_id=account.id,
            owner_id=owner.id,
            pet_id=pet.id,
            specialist_id=specialist.id,
            service_id=service.id,
            start_at=datetime(2025, 1, 6, 9, 0, tzinfo=UTC),
            end_at=datetime(2025, 1, 6, 10, 0, tzinfo=UTC),
            status=GroomingAppointmentStatus.SCHEDULED,
            price_snapshot=Decimal("65.00"),
        )
        session.add(appointment)

        await session.commit()

        return {
            "account_id": account.id,
            "location_id": location.id,
            "specialist_id": specialist.id,
            "service_id": service.id,
            "addon_id": addon.id,
        }


async def test_list_available_slots_respects_blocks(
    setup_account: dict[str, uuid.UUID],
) -> None:
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        slots = await list_available_slots(
            session,
            account_id=setup_account["account_id"],
            location_id=setup_account["location_id"],
            date_from=date(2025, 1, 6),
            date_to=date(2025, 1, 6),
            service_id=setup_account["service_id"],
            addon_ids=[setup_account["addon_id"]],
            specialist_id=setup_account["specialist_id"],
            slot_interval_minutes=15,
        )

    assert slots == [
        AvailableSlot(
            start_at=datetime(2025, 1, 6, 11, 0, tzinfo=UTC),
            end_at=datetime(2025, 1, 6, 12, 0, tzinfo=UTC),
            specialist_id=setup_account["specialist_id"],
        )
    ]
