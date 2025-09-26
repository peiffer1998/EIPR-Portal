"""Tests for grooming reporting endpoints."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import (
    CommissionType,
    GroomingAppointment,
    GroomingAppointmentStatus,
    GroomingService,
    OwnerProfile,
    Pet,
    PetType,
    Specialist,
    User,
    UserRole,
    UserStatus,
)

pytestmark = pytest.mark.asyncio


async def _authenticate(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _seed_appointments(
    db_url: str,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    report_date: datetime,
) -> uuid.UUID:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        specialist_user = User(
            account_id=account_id,
            email="specialist-report@example.com",
            hashed_password=get_password_hash("Spec123!"),
            first_name="Groom",
            last_name="Pro",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
        )
        session.add(specialist_user)
        await session.flush()

        specialist = Specialist(
            account_id=account_id,
            location_id=location_id,
            name="Kelly Groomer",
            user_id=specialist_user.id,
            commission_type=CommissionType.PERCENT,
            commission_rate=Decimal("15.00"),
        )
        session.add(specialist)
        await session.flush()

        service = GroomingService(
            account_id=account_id,
            code="DELUXE",
            name="Deluxe Groom",
            base_duration_minutes=60,
            base_price=Decimal("95.00"),
        )
        session.add(service)
        await session.flush()

        owner_user = User(
            account_id=account_id,
            email="owner-report@example.com",
            hashed_password=get_password_hash("Owner123!"),
            first_name="Pet",
            last_name="Parent",
            role=UserRole.PET_PARENT,
            status=UserStatus.ACTIVE,
        )
        session.add(owner_user)
        await session.flush()

        owner = OwnerProfile(user_id=owner_user.id)
        session.add(owner)
        await session.flush()

        pet = Pet(owner_id=owner.id, name="Riley", pet_type=PetType.DOG)
        session.add(pet)
        await session.flush()

        start_one = report_date.replace(hour=9, minute=0, second=0, microsecond=0)
        end_one = start_one + timedelta(hours=1)
        session.add(
            GroomingAppointment(
                account_id=account_id,
                owner_id=owner.id,
                pet_id=pet.id,
                specialist_id=specialist.id,
                service_id=service.id,
                start_at=start_one.astimezone(UTC),
                end_at=end_one.astimezone(UTC),
                status=GroomingAppointmentStatus.COMPLETED,
                price_snapshot=Decimal("95.00"),
                commission_type=CommissionType.PERCENT,
                commission_rate=Decimal("15.00"),
                commission_amount=Decimal("14.25"),
            )
        )

        start_two = report_date.replace(hour=11, minute=0, second=0, microsecond=0)
        end_two = start_two + timedelta(minutes=45)
        session.add(
            GroomingAppointment(
                account_id=account_id,
                owner_id=owner.id,
                pet_id=pet.id,
                specialist_id=specialist.id,
                service_id=service.id,
                start_at=start_two.astimezone(UTC),
                end_at=end_two.astimezone(UTC),
                status=GroomingAppointmentStatus.SCHEDULED,
                price_snapshot=Decimal("95.00"),
                commission_type=CommissionType.PERCENT,
                commission_rate=Decimal("15.00"),
                commission_amount=Decimal("14.25"),
            )
        )

        await session.commit()
        return specialist.id


async def test_grooming_reports(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_id: uuid.UUID = app_context["account_id"]
    location_id: uuid.UUID = app_context["location_id"]
    manager_email: str = app_context["manager_email"]
    manager_password: str = app_context["manager_password"]
    db_url = os.environ["DATABASE_URL"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    report_date = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    specialist_id = await _seed_appointments(
        db_url,
        account_id=account_id,
        location_id=location_id,
        report_date=report_date,
    )

    load_resp = await client.get(
        "/api/v1/grooming/reports/load",
        params={
            "report_date": report_date.date().isoformat(),
            "specialist_id": str(specialist_id),
        },
        headers=headers,
    )
    assert load_resp.status_code == 200, load_resp.text
    load_data = load_resp.json()
    assert load_data["total_minutes"] == 105
    assert load_data["status_counts"]["completed"] == 1
    assert load_data["status_counts"]["scheduled"] == 1

    commissions_resp = await client.get(
        "/api/v1/grooming/reports/commissions",
        params={
            "date_from": (report_date.date() - timedelta(days=1)).isoformat(),
            "date_to": (report_date.date() + timedelta(days=1)).isoformat(),
        },
        headers=headers,
    )
    assert commissions_resp.status_code == 200, commissions_resp.text
    commissions = commissions_resp.json()
    assert commissions
    entry = commissions[0]
    assert entry["total_commission"] == "28.50"
    assert entry["appointment_count"] == 2
