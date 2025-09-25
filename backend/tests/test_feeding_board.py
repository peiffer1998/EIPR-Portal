"""Feeding board endpoint tests."""

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
            "first_name": "Taylor",
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
            "end_at": (start_at + timedelta(hours=2)).isoformat(),
            "base_rate": "120.00",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_feeding_schedule(
    client: AsyncClient,
    headers: dict[str, str],
    reservation_id: str,
    *,
    scheduled_at: datetime,
    food: str,
    quantity: str,
) -> None:
    response = await client.post(
        f"/api/v1/reservations/{reservation_id}/feeding-schedules",
        json={
            "reservation_id": reservation_id,
            "scheduled_at": scheduled_at.isoformat(),
            "food": food,
            "quantity": quantity,
        },
        headers=headers,
    )
    assert response.status_code == 201


async def test_feeding_board_filters_by_service(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    location_id = str(app_context["location_id"])
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    _, pet_boarding = await _create_owner_and_pet(
        client,
        headers,
        location_id,
        email="boarding.owner@example.com",
        pet_name="Ranger",
    )
    _, pet_daycare = await _create_owner_and_pet(
        client,
        headers,
        location_id,
        email="daycare.owner@example.com",
        pet_name="Sunny",
    )

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    boarding_reservation = await _create_reservation(
        client,
        headers,
        pet_id=pet_boarding,
        location_id=location_id,
        reservation_type="boarding",
        start_at=now,
    )
    daycare_reservation = await _create_reservation(
        client,
        headers,
        pet_id=pet_daycare,
        location_id=location_id,
        reservation_type="daycare",
        start_at=now,
    )

    await _create_feeding_schedule(
        client,
        headers,
        reservation_id=boarding_reservation,
        scheduled_at=now.replace(hour=8),
        food="Chicken & Rice",
        quantity="1 cup",
    )
    await _create_feeding_schedule(
        client,
        headers,
        reservation_id=daycare_reservation,
        scheduled_at=now.replace(hour=12),
        food="Kibble",
        quantity="0.5 cup",
    )

    response = await client.get(
        "/api/v1/feeding/today",
        params={"location_id": location_id, "service": "boarding"},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["pet_name"] == "Ranger"
    assert payload[0]["owner_name"].startswith("Taylor")
    assert payload[0]["schedule_items"][0]["food"] == "Chicken & Rice"
    assert payload[0]["schedule_items"][0]["quantity"] == "1 cup"

    # Ensure validation rejects unsupported services
    invalid = await client.get(
        "/api/v1/feeding/today",
        params={"location_id": location_id, "service": "grooming"},
        headers=headers,
    )
    assert invalid.status_code == 422
