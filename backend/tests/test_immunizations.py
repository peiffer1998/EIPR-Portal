"""Tests for the health immunization endpoints."""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any
import uuid

import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import Account, User, UserRole, UserStatus

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
) -> tuple[str, str, str, str]:
    owner_email = f"{first_name.lower()}.{uuid.uuid4().hex[:6]}@example.com"
    owner_password = "StrongPass1!"
    owner_payload = {
        "first_name": first_name,
        "last_name": "Vaccinated",
        "email": owner_email,
        "password": owner_password,
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
    return owner_id, pet_id, owner_email, owner_password


async def test_immunization_status_flow(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    manager_token = await _authenticate(client, manager_email, manager_password)
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    owner_id, pet_id, owner_email, owner_password = await _create_owner_and_pet(
        client, manager_headers
    )

    type_payload = {
        "name": "Rabies",
        "required": True,
        "default_valid_days": 365,
    }
    type_resp = await client.post(
        "/api/v1/immunizations/types",
        json=type_payload,
        headers=manager_headers,
    )
    assert type_resp.status_code == 201
    type_id = type_resp.json()["id"]

    today = date.today()

    # current (verified) record
    current_resp = await client.post(
        f"/api/v1/immunizations/pets/{pet_id}/immunizations",
        json={
            "type_id": type_id,
            "issued_on": today.isoformat(),
            "expires_on": (today + timedelta(days=120)).isoformat(),
            "verified": True,
            "notes": "Initial",
        },
        headers=manager_headers,
    )
    assert current_resp.status_code == 201
    current_status = current_resp.json()
    assert current_status["is_current"] is True
    assert current_status["record"]["status"] == "current"

    # expiring record
    expiring_resp = await client.post(
        f"/api/v1/immunizations/pets/{pet_id}/immunizations",
        json={
            "type_id": type_id,
            "issued_on": today.isoformat(),
            "expires_on": (today + timedelta(days=5)).isoformat(),
            "verified": True,
            "notes": "Booster",
        },
        headers=manager_headers,
    )
    assert expiring_resp.status_code == 201
    expiring_status = expiring_resp.json()
    assert expiring_status["is_expiring"] is True
    assert expiring_status["record"]["status"] == "expiring"

    # expired record
    expired_resp = await client.post(
        f"/api/v1/immunizations/pets/{pet_id}/immunizations",
        json={
            "type_id": type_id,
            "issued_on": (today - timedelta(days=400)).isoformat(),
            "expires_on": (today - timedelta(days=5)).isoformat(),
            "verified": True,
        },
        headers=manager_headers,
    )
    assert expired_resp.status_code == 201
    expired_status = expired_resp.json()
    assert expired_status["is_expired"] is True
    assert expired_status["record"]["status"] == "expired"

    # pending (unverified) record
    pending_resp = await client.post(
        f"/api/v1/immunizations/pets/{pet_id}/immunizations",
        json={
            "type_id": type_id,
            "issued_on": today.isoformat(),
            "notes": "Owner uploaded",
        },
        headers=manager_headers,
    )
    assert pending_resp.status_code == 201
    pending_status = pending_resp.json()
    assert pending_status["is_pending"] is True
    assert pending_status["record"]["status"] == "pending"

    # manager list view
    list_resp = await client.get(
        f"/api/v1/immunizations/pets/{pet_id}/immunizations",
        headers=manager_headers,
    )
    assert list_resp.status_code == 200
    statuses = list_resp.json()
    statuses_by_id = {item["record"]["id"]: item for item in statuses}
    assert len(statuses_by_id) == 4
    assert statuses_by_id[pending_status["record"]["id"]]["is_required"] is True

    # owner can view their pet records
    owner_token = await _authenticate(client, owner_email, owner_password)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner_pet_resp = await client.get(
        f"/api/v1/immunizations/pets/{pet_id}/immunizations",
        headers=owner_headers,
    )
    assert owner_pet_resp.status_code == 200
    assert len(owner_pet_resp.json()) == 4

    owner_summary_resp = await client.get(
        f"/api/v1/immunizations/owners/{owner_id}/immunizations",
        headers=owner_headers,
    )
    assert owner_summary_resp.status_code == 200
    assert {item["record"]["status"] for item in owner_summary_resp.json()} >= {
        "pending",
        "current",
        "expiring",
        "expired",
    }

    # cross-account access should fail with 404
    outsider_password = "Outsider1!"
    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        other_account = Account(
            name="Other Resort", slug=f"other-{uuid.uuid4().hex[:8]}"
        )
        session.add(other_account)
        await session.flush()

        outsider = User(
            account_id=other_account.id,
            email="outsider.manager@example.com",
            hashed_password=get_password_hash(outsider_password),
            first_name="Olive",
            last_name="Outside",
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
        )
        session.add(outsider)
        await session.commit()

    outsider_token = await _authenticate(
        client, "outsider.manager@example.com", outsider_password
    )
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    outsider_pet_resp = await client.get(
        f"/api/v1/immunizations/pets/{pet_id}/immunizations",
        headers=outsider_headers,
    )
    assert outsider_pet_resp.status_code == 404

    outsider_owner_resp = await client.get(
        f"/api/v1/immunizations/owners/{owner_id}/immunizations",
        headers=outsider_headers,
    )
    assert outsider_owner_resp.status_code == 404
