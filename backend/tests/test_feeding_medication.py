"""Feeding and medication schedule API tests."""

from __future__ import annotations

from typing import Any
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import Account, Location, User, UserRole, UserStatus

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
    email_prefix: str = "feeding",
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
        "home_location_id": location_id,
        "name": f"{email_prefix.title()}Pet",
        "pet_type": "dog",
    }
    pet_resp = await client.post("/api/v1/pets", json=pet_payload, headers=headers)
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]
    return {"owner_id": owner_id, "pet_id": pet_id}


async def _create_reservation(
    client: AsyncClient,
    headers: dict[str, str],
    pet_id: str,
    location_id: str,
) -> str:
    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    end_at = start_at + timedelta(days=1)
    reservation_payload = {
        "pet_id": pet_id,
        "location_id": location_id,
        "reservation_type": "boarding",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "base_rate": "120.00",
    }
    response = await client.post(
        "/api/v1/reservations", json=reservation_payload, headers=headers
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_feeding_and_medication_schedule_lifecycle(
    app_context: dict[str, Any],
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    ids = await _create_owner_and_pet(client, headers, location_id)
    reservation_id = await _create_reservation(
        client, headers, ids["pet_id"], location_id
    )

    feeding_payload = {
        "reservation_id": reservation_id,
        "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
        "food": "Kibble",
        "quantity": "2 cups",
        "notes": "Warm water mix",
    }
    feeding_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/feeding-schedules",
        json=feeding_payload,
        headers=headers,
    )
    assert feeding_resp.status_code == 201
    feeding_id = feeding_resp.json()["id"]

    list_feeding = await client.get(
        f"/api/v1/reservations/{reservation_id}/feeding-schedules",
        headers=headers,
    )
    assert list_feeding.status_code == 200
    assert any(item["id"] == feeding_id for item in list_feeding.json())

    update_feeding_resp = await client.patch(
        f"/api/v1/reservations/{reservation_id}/feeding-schedules/{feeding_id}",
        json={"quantity": "1.5 cups"},
        headers=headers,
    )
    assert update_feeding_resp.status_code == 200
    assert update_feeding_resp.json()["quantity"] == "1.5 cups"

    mismatch_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/feeding-schedules",
        json={**feeding_payload, "reservation_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert mismatch_resp.status_code == 400

    medication_payload = {
        "reservation_id": reservation_id,
        "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=7)).isoformat(),
        "medication": "Antibiotic",
        "dosage": "1 pill",
        "notes": "Give with food",
    }
    medication_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/medication-schedules",
        json=medication_payload,
        headers=headers,
    )
    assert medication_resp.status_code == 201
    medication_id = medication_resp.json()["id"]

    list_medication = await client.get(
        f"/api/v1/reservations/{reservation_id}/medication-schedules",
        headers=headers,
    )
    assert list_medication.status_code == 200
    assert any(item["id"] == medication_id for item in list_medication.json())

    reservation_resp = await client.get(
        f"/api/v1/reservations/{reservation_id}",
        headers=headers,
    )
    assert reservation_resp.status_code == 200
    reservation_body = reservation_resp.json()
    assert any(
        item["id"] == feeding_id for item in reservation_body["feeding_schedules"]
    )
    assert any(
        item["id"] == medication_id for item in reservation_body["medication_schedules"]
    )

    delete_feeding = await client.delete(
        f"/api/v1/reservations/{reservation_id}/feeding-schedules/{feeding_id}",
        headers=headers,
    )
    assert delete_feeding.status_code == 204

    delete_medication = await client.delete(
        f"/api/v1/reservations/{reservation_id}/medication-schedules/{medication_id}",
        headers=headers,
    )
    assert delete_medication.status_code == 204

    final_reservation = await client.get(
        f"/api/v1/reservations/{reservation_id}",
        headers=headers,
    )
    assert final_reservation.status_code == 200
    body = final_reservation.json()
    assert body["feeding_schedules"] == []
    assert body["medication_schedules"] == []


async def test_schedule_account_isolation(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}
    ids = await _create_owner_and_pet(
        client, headers, location_id, email_prefix="isolation"
    )
    reservation_id = await _create_reservation(
        client, headers, ids["pet_id"], location_id
    )

    feeding_payload = {
        "reservation_id": reservation_id,
        "scheduled_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "food": "Canned",
    }
    feed_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/feeding-schedules",
        json=feeding_payload,
        headers=headers,
    )
    assert feed_resp.status_code == 201

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        other_account = Account(
            name="Other Resort", slug=f"other-{uuid.uuid4().hex[:6]}"
        )
        session.add(other_account)
        await session.flush()

        session.add(
            Location(
                account_id=other_account.id,
                name="Iowa City",
                timezone="UTC",
            )
        )
        other_password = "Passw0rd!"
        other_manager = User(
            account_id=other_account.id,
            email="other.manager@example.com",
            hashed_password=get_password_hash(other_password),
            first_name="Other",
            last_name="Manager",
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
        )
        session.add(other_manager)
        await session.commit()

    other_token = await _authenticate(
        client, "other.manager@example.com", other_password
    )
    other_headers = {"Authorization": f"Bearer {other_token}"}

    list_resp = await client.get(
        f"/api/v1/reservations/{reservation_id}/feeding-schedules",
        headers=other_headers,
    )
    assert list_resp.status_code == 404

    create_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/medication-schedules",
        json={
            "reservation_id": reservation_id,
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "medication": "Painkiller",
        },
        headers=other_headers,
    )
    assert create_resp.status_code == 404
