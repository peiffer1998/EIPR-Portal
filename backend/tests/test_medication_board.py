"""Medication board endpoint tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient

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
    email: str,
    pet_name: str,
) -> tuple[str, str]:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Jordan",
            "last_name": "Client",
            "email": email,
            "password": "StrongPass1!",
        },
        headers=headers,
    )
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["id"]

    pet_resp = await client.post(
        "/api/v1/pets",
        json={
            "owner_id": owner_id,
            "home_location_id": location_id,
            "name": pet_name,
            "pet_type": "dog",
        },
        headers=headers,
    )
    assert pet_resp.status_code == 201
    return owner_id, pet_resp.json()["id"]


async def _create_reservation(
    client: AsyncClient,
    headers: dict[str, str],
    pet_id: str,
    location_id: str,
    *,
    reservation_type: str,
    start_at: datetime,
) -> str:
    response = await client.post(
        "/api/v1/reservations",
        json={
            "pet_id": pet_id,
            "location_id": location_id,
            "reservation_type": reservation_type,
            "start_at": start_at.isoformat(),
            "end_at": (start_at + timedelta(days=1)).isoformat(),
            "base_rate": "145.00",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_medication_schedule(
    client: AsyncClient,
    headers: dict[str, str],
    reservation_id: str,
    *,
    scheduled_at: datetime,
    medication: str,
    dosage: str,
) -> None:
    response = await client.post(
        f"/api/v1/reservations/{reservation_id}/medication-schedules",
        json={
            "reservation_id": reservation_id,
            "scheduled_at": scheduled_at.isoformat(),
            "medication": medication,
            "dosage": dosage,
        },
        headers=headers,
    )
    assert response.status_code == 201


async def test_medication_board_returns_entries(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    location_id = str(app_context["location_id"])
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    _, pet_id = await _create_owner_and_pet(
        client,
        headers,
        location_id,
        email="med.owner@example.com",
        pet_name="Mochi",
    )

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    reservation_id = await _create_reservation(
        client,
        headers,
        pet_id=pet_id,
        location_id=location_id,
        reservation_type="boarding",
        start_at=now,
    )

    await _create_medication_schedule(
        client,
        headers,
        reservation_id=reservation_id,
        scheduled_at=now.replace(hour=9),
        medication="Carprofen",
        dosage="25mg",
    )
    await _create_medication_schedule(
        client,
        headers,
        reservation_id=reservation_id,
        scheduled_at=now.replace(hour=17),
        medication="Carprofen",
        dosage="25mg",
    )

    response = await client.get(
        "/api/v1/medication/today",
        params={"location_id": location_id},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["pet_name"] == "Mochi"
    assert len(payload[0]["schedule_items"]) == 2
    times = [item["scheduled_at"] for item in payload[0]["schedule_items"]]
    assert times == sorted(times)
