"""Capacity management API tests."""
from __future__ import annotations

import uuid

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


async def test_capacity_crud(app_context: dict[str, object], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    # Create a new location for testing
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        account_id = app_context["account_id"]  # type: ignore[index]
        location = Location(
            account_id=account_id,
            name="North Annex",
            timezone="UTC",
        )
        session.add(location)
        await session.commit()
        await session.refresh(location)
        location_id = str(location.id)

    create_resp = await client.post(
        "/api/v1/capacity",
        json={
            "location_id": location_id,
            "reservation_type": "grooming",
            "max_active": 3,
            "waitlist_limit": 5,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    rule_id = create_resp.json()["id"]

    list_resp = await client.get(f"/api/v1/capacity/locations/{location_id}", headers=headers)
    assert list_resp.status_code == 200
    rules = list_resp.json()
    assert any(rule["id"] == rule_id for rule in rules)

    update_resp = await client.patch(
        f"/api/v1/capacity/{rule_id}",
        json={"max_active": 4, "waitlist_limit": 6},
        headers=headers,
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["max_active"] == 4
    assert body["waitlist_limit"] == 6

    delete_resp = await client.delete(f"/api/v1/capacity/{rule_id}", headers=headers)
    assert delete_resp.status_code == 204

    final_list = await client.get(f"/api/v1/capacity/locations/{location_id}", headers=headers)
    assert final_list.status_code == 200
    assert not any(rule["id"] == rule_id for rule in final_list.json())
