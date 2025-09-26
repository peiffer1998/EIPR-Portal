"""API tests for deposit endpoints."""

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


async def _seed_reservation(
    client: AsyncClient,
    headers: dict[str, str],
    location_id: str,
    *,
    owner_email: str,
) -> str:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Casey",
            "last_name": "Deposit",
            "email": owner_email,
            "password": "DepositPass1!",
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
            "name": "DepositDog",
            "pet_type": "dog",
        },
        headers=headers,
    )
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]

    start_at = datetime.now(timezone.utc) + timedelta(days=3)
    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={
            "pet_id": pet_id,
            "location_id": location_id,
            "reservation_type": "boarding",
            "start_at": start_at.isoformat(),
            "end_at": (start_at + timedelta(days=2)).isoformat(),
            "base_rate": "120.00",
        },
        headers=headers,
    )
    assert reservation_resp.status_code == 201
    return reservation_resp.json()["id"]


async def test_deposit_lifecycle_api(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    manager_token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {manager_token}"}
    reservation_id = await _seed_reservation(
        client,
        headers,
        location_id,
        owner_email="deposit-owner@example.com",
    )

    hold_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/deposits/hold",
        json={"amount": "50.00"},
        headers=headers,
    )
    assert hold_resp.status_code == 201
    assert hold_resp.json()["status"] == "held"

    consume_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/deposits/consume",
        json={"amount": "50.00"},
        headers=headers,
    )
    assert consume_resp.status_code == 200
    assert consume_resp.json()["status"] == "consumed"

    # Hold again to test refund path
    hold_again = await client.post(
        f"/api/v1/reservations/{reservation_id}/deposits/hold",
        json={"amount": "30.00"},
        headers=headers,
    )
    assert hold_again.status_code == 201

    refund_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/deposits/refund",
        json={"amount": "30.00"},
        headers=headers,
    )
    assert refund_resp.status_code == 200
    assert refund_resp.json()["status"] == "refunded"

    # Ensure pet parent cannot perform deposit actions
    owner_login = await client.post(
        "/api/v1/auth/token",
        data={"username": "deposit-owner@example.com", "password": "DepositPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert owner_login.status_code == 200
    owner_token = owner_login.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    forbidden_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/deposits/hold",
        json={"amount": "25.00"},
        headers=owner_headers,
    )
    assert forbidden_resp.status_code == 403
