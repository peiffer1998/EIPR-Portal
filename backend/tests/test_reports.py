"""Reporting and analytics API tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
) -> tuple[str, str]:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Casey",
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
            "name": "Scout",
            "pet_type": "dog",
        },
        headers=headers,
    )
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]
    return owner_id, pet_id


async def _create_reservation(
    client: AsyncClient,
    headers: dict[str, str],
    pet_id: str,
    location_id: str,
    *,
    start_at: datetime,
    base_rate: str,
) -> str:
    response = await client.post(
        "/api/v1/reservations",
        json={
            "pet_id": pet_id,
            "location_id": location_id,
            "reservation_type": "boarding",
            "start_at": start_at.isoformat(),
            "end_at": (start_at + timedelta(days=2)).isoformat(),
            "base_rate": base_rate,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _progress_reservation_to_checkout(
    client: AsyncClient,
    headers: dict[str, str],
    reservation_id: str,
) -> None:
    confirm_resp = await client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "confirmed"},
        headers=headers,
    )
    assert confirm_resp.status_code == 200

    check_in_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/check-in",
        headers=headers,
    )
    assert check_in_resp.status_code == 200

    check_out_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/check-out",
        headers=headers,
    )
    assert check_out_resp.status_code == 200


async def test_occupancy_report(app_context: dict[str, object]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    owner_id, pet_id = await _create_owner_and_pet(
        client,
        headers,
        location_id,
        email="report.owner@example.com",
    )

    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    reservation_id = await _create_reservation(
        client,
        headers,
        pet_id=pet_id,
        location_id=location_id,
        start_at=start_at,
        base_rate="150.00",
    )

    report_resp = await client.get(
        "/api/v1/reports/occupancy",
        params={
            "start_date": start_at.date().isoformat(),
            "end_date": start_at.date().isoformat(),
            "location_id": location_id,
        },
        headers=headers,
    )
    assert report_resp.status_code == 200
    entries = report_resp.json()
    assert any(entry["booked"] >= 1 for entry in entries)


async def test_revenue_report(app_context: dict[str, object]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    owner_id, pet_id = await _create_owner_and_pet(
        client,
        headers,
        location_id,
        email="revenue.owner@example.com",
    )

    start_at = datetime.now(timezone.utc) - timedelta(days=5)
    reservation_id = await _create_reservation(
        client,
        headers,
        pet_id=pet_id,
        location_id=location_id,
        start_at=start_at,
        base_rate="200.00",
    )

    await _progress_reservation_to_checkout(client, headers, reservation_id)

    revenue_resp = await client.get(
        "/api/v1/reports/revenue",
        params={
            "start_date": (start_at.date() - timedelta(days=1)).isoformat(),
            "end_date": (start_at.date() + timedelta(days=7)).isoformat(),
        },
        headers=headers,
    )
    assert revenue_resp.status_code == 200
    body = revenue_resp.json()
    assert body["entries"]
    assert body["grand_total"] == "200.00"
