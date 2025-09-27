"""Reservation API integration tests."""

from __future__ import annotations

from typing import Any
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


async def _create_owner_and_pet(
    client: AsyncClient,
    headers: dict[str, str],
    location_id: str,
    *,
    email_prefix: str = "taylor",
) -> dict[str, str]:
    owner_payload = {
        "first_name": email_prefix.capitalize(),
        "last_name": "Guardian",
        "email": f"{email_prefix}.guardian@example.com",
        "password": "StrongPass1!",
    }
    owner_resp = await client.post(
        "/api/v1/owners", json=owner_payload, headers=headers
    )
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["id"]

    pet_payload = {
        "owner_id": owner_id,
        "home_location_id": str(location_id),
        "name": f"{email_prefix.title()}Pet",
        "pet_type": "dog",
    }
    pet_resp = await client.post("/api/v1/pets", json=pet_payload, headers=headers)
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]
    return {"owner_id": owner_id, "pet_id": pet_id}


async def test_reservation_lifecycle(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

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
    create_resp = await client.post(
        "/api/v1/reservations", json=create_payload, headers=headers
    )
    assert create_resp.status_code == 201
    reservation = create_resp.json()
    reservation_id = reservation["id"]
    assert reservation["status"] == "requested"
    assert reservation["pet"]["id"] == ids["pet_id"]
    assert reservation["pet"]["name"].endswith("Pet")
    assert reservation["check_in_at"] is None
    assert reservation["check_out_at"] is None
    assert reservation["kennel_id"] is None

    # Assign a run
    run_uuid = str(uuid.uuid4())
    move_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/move-run",
        json={"run_id": run_uuid},
        headers=headers,
    )
    assert move_resp.status_code == 200
    assert move_resp.json()["kennel_id"] == run_uuid

    # Clearing the run
    clear_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/move-run",
        json={"run_id": None},
        headers=headers,
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["kennel_id"] is None

    # Accept the reservation request
    accept_resp = await client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "accepted"},
        headers=headers,
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "accepted"

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

    # Valid transitions via dedicated check-in/out endpoints
    kennel_id = str(uuid.uuid4())
    check_in_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/check-in",
        json={"kennel_id": kennel_id},
        headers=headers,
    )
    assert check_in_resp.status_code == 200
    check_in_body = check_in_resp.json()
    assert check_in_body["status"] == "checked_in"
    assert check_in_body["check_in_at"] is not None
    assert check_in_body["kennel_id"] == kennel_id

    checkout_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    check_out_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/check-out",
        json={"check_out_at": checkout_time},
        headers=headers,
    )
    assert check_out_resp.status_code == 200
    check_out_body = check_out_resp.json()
    assert check_out_body["status"] == "checked_out"
    response_checkout = datetime.fromisoformat(check_out_body["check_out_at"])
    if response_checkout.tzinfo is None:
        response_checkout = response_checkout.replace(tzinfo=timezone.utc)
    expected_checkout = datetime.fromisoformat(checkout_time)
    if expected_checkout.tzinfo is None:
        expected_checkout = expected_checkout.replace(tzinfo=timezone.utc)
    assert response_checkout == expected_checkout

    list_resp = await client.get("/api/v1/reservations", headers=headers)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert any(item["id"] == reservation_id for item in body)
    assert any(
        item.get("pet", {}).get("name") == reservation["pet"]["name"] for item in body
    )

    delete_resp = await client.delete(
        f"/api/v1/reservations/{reservation_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    get_deleted = await client.get(
        f"/api/v1/reservations/{reservation_id}", headers=headers
    )
    assert get_deleted.status_code == 404


async def test_reservation_account_isolation(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

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
        other_account = Account(
            name="South Location", slug=f"south-{uuid.uuid4().hex[:6]}"
        )
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

    other_token = await _authenticate(
        client, "south.manager@example.com", "SecureSouth1!"
    )
    other_headers = {"Authorization": f"Bearer {other_token}"}

    forbidden_fetch = await client.get(
        f"/api/v1/reservations/{reservation_id}", headers=other_headers
    )
    assert forbidden_fetch.status_code == 404


async def test_reservation_capacity_limit(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    first_ids = await _create_owner_and_pet(
        client, headers, location_id, email_prefix="alex"
    )
    second_ids = await _create_owner_and_pet(
        client, headers, location_id, email_prefix="blair"
    )

    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    end_at = start_at + timedelta(days=1)

    create_payload = {
        "pet_id": first_ids["pet_id"],
        "location_id": location_id,
        "reservation_type": "boarding",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "base_rate": "120.00",
    }
    create_resp = await client.post(
        "/api/v1/reservations", json=create_payload, headers=headers
    )
    assert create_resp.status_code == 201
    reservation_id = create_resp.json()["id"]

    accept_resp = await client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "accepted"},
        headers=headers,
    )
    assert accept_resp.status_code == 200

    overlap_payload = {
        "pet_id": second_ids["pet_id"],
        "location_id": location_id,
        "reservation_type": "boarding",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "base_rate": "120.00",
    }
    overlap_resp = await client.post(
        "/api/v1/reservations", json=overlap_payload, headers=headers
    )
    assert overlap_resp.status_code == 400
    assert "capacity" in overlap_resp.json()["detail"].lower()

    availability_resp = await client.get(
        "/api/v1/reservations/availability/daily",
        params={
            "location_id": location_id,
            "reservation_type": "boarding",
            "start_date": start_at.date().isoformat(),
            "end_date": end_at.date().isoformat(),
        },
        headers=headers,
    )
    assert availability_resp.status_code == 200
    body = availability_resp.json()
    assert body["location_id"] == location_id
    assert body["reservation_type"] == "boarding"
    assert body["days"][0]["capacity"] == 1
    assert body["days"][0]["booked"] == 1
    assert body["days"][0]["available"] == 0

    cancel_resp = await client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "canceled"},
        headers=headers,
    )
    assert cancel_resp.status_code == 200

    second_attempt = await client.post(
        "/api/v1/reservations", json=overlap_payload, headers=headers
    )
    assert second_attempt.status_code == 201
