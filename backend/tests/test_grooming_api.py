"""Integration tests for the grooming staff API."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import OwnerProfile, Pet, PetType, User, UserRole, UserStatus

pytestmark = pytest.mark.asyncio


async def _authenticate(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _seed_owner_and_pet(
    db_url: str, account_id: uuid.UUID, *, email: str = "guest@example.com"
) -> tuple[uuid.UUID, uuid.UUID]:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        user = User(
            account_id=account_id,
            email=email,
            hashed_password=get_password_hash("Owner123!"),
            first_name="Owner",
            last_name="Example",
            role=UserRole.PET_PARENT,
            status=UserStatus.ACTIVE,
        )
        session.add(user)
        await session.flush()

        owner = OwnerProfile(user_id=user.id)
        session.add(owner)
        await session.flush()

        pet = Pet(owner_id=owner.id, name="Comet", pet_type=PetType.DOG)
        session.add(pet)
        await session.commit()
        return owner.id, pet.id


async def test_grooming_workflow(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_id: uuid.UUID = app_context["account_id"]
    location_id: uuid.UUID = app_context["location_id"]
    manager_email: str = app_context["manager_email"]
    manager_password: str = app_context["manager_password"]
    db_url: str = os.environ["DATABASE_URL"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    specialist_payload = {
        "name": "Jordan Stylist",
        "location_id": str(location_id),
        "commission_type": "percent",
        "commission_rate": "10.00",
        "active": True,
    }
    specialist_resp = await client.post(
        "/api/v1/grooming/specialists", json=specialist_payload, headers=headers
    )
    assert specialist_resp.status_code == 201, specialist_resp.text
    specialist_id = specialist_resp.json()["id"]

    weekday = (datetime.now() + timedelta(days=1)).weekday()
    schedule_resp = await client.post(
        f"/api/v1/grooming/specialists/{specialist_id}/schedules",
        json={"weekday": weekday, "start_time": "09:00", "end_time": "17:00"},
        headers=headers,
    )
    assert schedule_resp.status_code == 201, schedule_resp.text

    time_off_resp = await client.post(
        f"/api/v1/grooming/specialists/{specialist_id}/time-off",
        json={
            "starts_at": (datetime.now(UTC) + timedelta(days=1, hours=4)).isoformat(),
            "ends_at": (datetime.now(UTC) + timedelta(days=1, hours=5)).isoformat(),
            "reason": "Lunch",
        },
        headers=headers,
    )
    assert time_off_resp.status_code == 201, time_off_resp.text

    service_resp = await client.post(
        "/api/v1/grooming/services",
        json={
            "code": "FULL",
            "name": "Full Groom",
            "base_duration_minutes": 60,
            "base_price": "80.00",
        },
        headers=headers,
    )
    assert service_resp.status_code == 201
    service_id = service_resp.json()["id"]

    addon_resp = await client.post(
        "/api/v1/grooming/addons",
        json={
            "code": "NAILS",
            "name": "Nail Trim",
            "add_duration_minutes": 15,
            "add_price": "20.00",
        },
        headers=headers,
    )
    assert addon_resp.status_code == 201
    addon_id = addon_resp.json()["id"]

    owner_id, pet_id = await _seed_owner_and_pet(db_url, account_id)

    target_date = datetime.now().date() + timedelta(days=1)
    availability_resp = await client.get(
        "/api/v1/grooming/availability",
        params={
            "date_from": target_date.isoformat(),
            "date_to": target_date.isoformat(),
            "service_id": service_id,
            "location_id": str(location_id),
            "addons": addon_id,
            "slot_interval_minutes": 30,
            "specialist_id": specialist_id,
        },
        headers=headers,
    )
    assert availability_resp.status_code == 200, availability_resp.text
    slots = availability_resp.json()
    assert slots, "expected at least one slot"
    slot_start = slots[0]["start_at"]

    appointment_resp = await client.post(
        "/api/v1/grooming/appointments",
        json={
            "owner_id": str(owner_id),
            "pet_id": str(pet_id),
            "specialist_id": specialist_id,
            "service_id": service_id,
            "addon_ids": [addon_id],
            "start_at": slot_start,
            "notes": "First-time groom",
        },
        headers=headers,
    )
    assert appointment_resp.status_code == 201, appointment_resp.text
    appointment = appointment_resp.json()
    appointment_id = appointment["id"]
    assert appointment["status"] == "scheduled"
    assert appointment["price_snapshot"] == "100.00"

    reschedule_resp = await client.patch(
        f"/api/v1/grooming/appointments/{appointment_id}/reschedule",
        json={"new_start_at": slots[-1]["start_at"]},
        headers=headers,
    )
    assert reschedule_resp.status_code == 200, reschedule_resp.text

    status_resp = await client.post(
        f"/api/v1/grooming/appointments/{appointment_id}/status",
        json={"new_status": "checked_in"},
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "checked_in"

    cancel_resp = await client.post(
        f"/api/v1/grooming/appointments/{appointment_id}/cancel",
        json={"reason": "Pet unwell"},
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "canceled"

    list_resp = await client.get(
        "/api/v1/grooming/appointments",
        headers=headers,
    )
    assert list_resp.status_code == 200
    listing = list_resp.json()
    assert listing
    entry = listing[0]
    assert entry["service_name"] == "Full Groom"
    assert entry["specialist_name"] == "Jordan Stylist"
