"""Reservation API integration tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import Account, Location, OwnerProfile, User, UserRole, UserStatus

pytestmark = pytest.mark.asyncio


async def _authenticate(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _create_owner_and_pet(client: AsyncClient, headers: dict[str, str], location_id: str) -> dict[str, str]:
    owner_payload = {
        "first_name": "Taylor",
        "last_name": "Guardian",
        "email": "taylor.guardian@example.com",
        "password": "StrongPass1!",
    }
    owner_resp = await client.post("/api/v1/owners", json=owner_payload, headers=headers)
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["id"]

    pet_payload = {
        "owner_id": owner_id,
        "home_location_id": location_id,
        "name": "Indy",
        "pet_type": "dog",
    }
    pet_resp = await client.post("/api/v1/pets", json=pet_payload, headers=headers)
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]
    return {"owner_id": owner_id, "pet_id": pet_id}


async def test_reservation_lifecycle(app_context: dict[str, object]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = app_context["location_id"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    ids = await _create_owner_and_pet(client, headers, location_id)

    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    end_at = start_at + timedelta(days=3)

    create_payload = {
        "pet_id": ids["pet_id"],
        "location_id": location_id,
        "reservation_type": "boarding",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "base_rate": "150.00",
        "notes": "Owner requests webcam access",
    }
    create_resp = await client.post("/api/v1/reservations", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    reservation = create_resp.json()
    reservation_id = reservation["id"]
    assert reservation["status"] == "requested"

    # Promote to confirmed
    confirm_resp = await client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "confirmed"},
        headers=headers,
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    # Invalid transition: confirmed -> requested (disallowed)
    invalid_resp = await client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "checked_out"},
        headers=headers,
    )
    assert invalid_resp.status_code == 400

    # Valid transitions to checked_in then checked_out
    check_in_resp = await client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "checked_in"},
        headers=headers,
    )
    assert check_in_resp.status_code == 200
    assert check_in_resp.json()["status"] == "checked_in"

    check_out_resp = await client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "checked_out"},
        headers=headers,
    )
    assert check_out_resp.status_code == 200
    assert check_out_resp.json()["status"] == "checked_out"

    list_resp = await client.get("/api/v1/reservations", headers=headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == reservation_id for item in list_resp.json())

    delete_resp = await client.delete(f"/api/v1/reservations/{reservation_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_deleted = await client.get(f"/api/v1/reservations/{reservation_id}", headers=headers)
    assert get_deleted.status_code == 404


async def test_reservation_account_isolation(app_context: dict[str, object], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = app_context["location_id"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    ids = await _create_owner_and_pet(client, headers, location_id)

    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    end_at = start_at + timedelta(days=2)

    create_resp = await client.post(
        "/api/v1/reservations",
        json={
            "pet_id": ids["pet_id"],
            "location_id": location_id,
            "reservation_type": "daycare",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "base_rate": "85.00",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    reservation_id = create_resp.json()["id"]

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        other_account = Account(name="South Location", slug=f"south-{uuid.uuid4().hex[:6]}")
        session.add(other_account)
        await session.flush()

        other_location = Location(
            account_id=other_account.id,
            name="Iowa City",
            timezone="UTC",
        )
        session.add(other_location)

        other_manager = User(
            account_id=other_account.id,
            email="south.manager@example.com",
            hashed_password=get_password_hash("SecureSouth1!"),
            first_name="Sam",
            last_name="Manager",
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
        )
        session.add(other_manager)

        stray_owner = OwnerProfile(
            user=User(
                account_id=other_account.id,
                email="other.parent@example.com",
                hashed_password=get_password_hash("Guardian1!"),
                first_name="Other",
                last_name="Parent",
                role=UserRole.PET_PARENT,
                status=UserStatus.ACTIVE,
            )
        )
        session.add(stray_owner)
        await session.commit()

    other_token = await _authenticate(client, "south.manager@example.com", "SecureSouth1!")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    forbidden_fetch = await client.get(f"/api/v1/reservations/{reservation_id}", headers=other_headers)
    assert forbidden_fetch.status_code == 404
