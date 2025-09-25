"""Location capacity rule API tests."""
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


async def _create_location(db_url: str, account_id: uuid.UUID, name: str) -> uuid.UUID:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        location = Location(
            account_id=account_id,
            name=name,
            timezone="UTC",
        )
        session.add(location)
        await session.commit()
        await session.refresh(location)
        return location.id


async def test_capacity_rules_crud(app_context: dict[str, object], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    account_id = app_context["account_id"]  # type: ignore[index]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    location_id = await _create_location(db_url, account_id, "North Annex")

    create_resp = await client.post(
        f"/api/v1/locations/{location_id}/capacity-rules",
        json={
            "location_id": str(location_id),
            "reservation_type": "grooming",
            "max_active": 3,
            "waitlist_limit": 5,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    rule_id = create_resp.json()["id"]

    list_resp = await client.get(
        f"/api/v1/locations/{location_id}/capacity-rules",
        headers=headers,
    )
    assert list_resp.status_code == 200
    rules = list_resp.json()
    assert any(rule["id"] == rule_id for rule in rules)

    update_resp = await client.patch(
        f"/api/v1/locations/{location_id}/capacity-rules/{rule_id}",
        json={"max_active": 4, "waitlist_limit": 6},
        headers=headers,
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["max_active"] == 4
    assert body["waitlist_limit"] == 6

    delete_resp = await client.delete(
        f"/api/v1/locations/{location_id}/capacity-rules/{rule_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 204

    final_list = await client.get(
        f"/api/v1/locations/{location_id}/capacity-rules",
        headers=headers,
    )
    assert final_list.status_code == 200
    assert not any(rule["id"] == rule_id for rule in final_list.json())


async def test_capacity_rules_uniqueness(app_context: dict[str, object], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    account_id = app_context["account_id"]  # type: ignore[index]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    location_id = await _create_location(db_url, account_id, "South Annex")

    payload = {
        "location_id": str(location_id),
        "reservation_type": "boarding",
        "max_active": 10,
    }

    first_resp = await client.post(
        f"/api/v1/locations/{location_id}/capacity-rules",
        json=payload,
        headers=headers,
    )
    assert first_resp.status_code == 201

    duplicate_resp = await client.post(
        f"/api/v1/locations/{location_id}/capacity-rules",
        json=payload,
        headers=headers,
    )
    assert duplicate_resp.status_code == 400


async def test_capacity_rules_account_isolation(app_context: dict[str, object], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        other_account = Account(name="Other Resort", slug=f"other-{uuid.uuid4().hex[:6]}")
        session.add(other_account)
        await session.flush()

        other_location = Location(
            account_id=other_account.id,
            name="Iowa City",
            timezone="UTC",
        )
        session.add(other_location)

        other_manager_password = "OtherPass1!"
        other_manager = User(
            account_id=other_account.id,
            email="other.manager@example.com",
            hashed_password=get_password_hash(other_manager_password),
            first_name="Owen",
            last_name="Manager",
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
        )
        session.add(other_manager)
        await session.commit()
        other_location_id = other_location.id

    token = await _authenticate(client, "other.manager@example.com", other_manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    invalid_resp = await client.get(
        f"/api/v1/locations/{app_context['location_id']}/capacity-rules",
        headers=headers,
    )
    assert invalid_resp.status_code == 404

    create_resp = await client.post(
        f"/api/v1/locations/{app_context['location_id']}/capacity-rules",
        json={
            "location_id": str(app_context["location_id"]),
            "reservation_type": "training",
        },
        headers=headers,
    )
    assert create_resp.status_code == 404

    own_create = await client.post(
        f"/api/v1/locations/{other_location_id}/capacity-rules",
        json={
            "location_id": str(other_location_id),
            "reservation_type": "training",
        },
        headers=headers,
    )
    assert own_create.status_code == 201
