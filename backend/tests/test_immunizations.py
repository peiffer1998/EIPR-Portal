"""Integration tests for immunization API."""

from __future__ import annotations

from datetime import date, timedelta
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
    *,
    first_name: str = "Jamie",
) -> tuple[str, str]:
    owner_payload = {
        "first_name": first_name,
        "last_name": "Vaccinated",
        "email": f"{first_name.lower()}.vaccinated@example.com",
        "password": "StrongPass1!",
    }
    owner_resp = await client.post(
        "/api/v1/owners", json=owner_payload, headers=headers
    )
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["id"]

    pet_payload = {
        "owner_id": owner_id,
        "home_location_id": None,
        "name": f"{first_name}Pet",
        "pet_type": "dog",
    }
    pet_resp = await client.post("/api/v1/pets", json=pet_payload, headers=headers)
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]
    return owner_id, pet_id


async def test_immunization_lifecycle(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    # create owner and pet
    _, pet_id = await _create_owner_and_pet(client, headers)

    # create immunization type
    type_payload = {
        "name": "Rabies",
        "description": "Rabies vaccination",
        "validity_days": 365,
        "reminder_days_before": 30,
        "is_required": True,
    }
    type_resp = await client.post(
        "/api/v1/immunizations/types",
        json=type_payload,
        headers=headers,
    )
    assert type_resp.status_code == 201
    immunization_type = type_resp.json()

    today = date.today()
    record_payload = {
        "pet_id": pet_id,
        "immunization_type_id": immunization_type["id"],
        "received_on": today.isoformat(),
        "expires_on": (today + timedelta(days=10)).isoformat(),
        "notes": "Initial dose",
        "document": {
            "file_name": "rabies.pdf",
            "content_type": "application/pdf",
            "url": "https://example.com/rabies.pdf",
            "pet_id": pet_id,
        },
    }
    record_resp = await client.post(
        "/api/v1/immunizations/records",
        json=record_payload,
        headers=headers,
    )
    assert record_resp.status_code == 201
    record = record_resp.json()
    assert record["status"] == "expiring"
    assert record["document"]["file_name"] == "rabies.pdf"

    expired_payload = {
        "pet_id": pet_id,
        "immunization_type_id": immunization_type["id"],
        "received_on": (today - timedelta(days=400)).isoformat(),
        "expires_on": (today - timedelta(days=5)).isoformat(),
    }
    expired_resp = await client.post(
        "/api/v1/immunizations/records",
        json=expired_payload,
        headers=headers,
    )
    assert expired_resp.status_code == 201
    expired_record = expired_resp.json()

    evaluate_resp = await client.post(
        "/api/v1/immunizations/evaluate",
        headers=headers,
    )
    assert evaluate_resp.status_code == 200

    all_records_resp = await client.get(
        "/api/v1/immunizations/records",
        headers=headers,
    )
    assert all_records_resp.status_code == 200
    all_statuses = {item["id"]: item["status"] for item in all_records_resp.json()}
    assert all_statuses[record["id"]] == "expiring"
    assert all_statuses[expired_record["id"]] == "expired"

    list_resp = await client.get(
        "/api/v1/immunizations/records",
        params={"status": "expiring"},
        headers=headers,
    )
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) == 1
    assert listed[0]["id"] == record["id"]
