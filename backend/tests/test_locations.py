"""Location administration tests."""
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


async def test_location_crud_superadmin(app_context: dict[str, object], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_id = app_context["account_id"]

    sessionmaker = get_sessionmaker(db_url)
    superadmin_password = "SuperPass1!"
    async with sessionmaker() as session:
        superadmin = User(
            account_id=account_id,
            email="superadmin@example.com",
            hashed_password=get_password_hash(superadmin_password),
            first_name="Sydney",
            last_name="Root",
            role=UserRole.SUPERADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(superadmin)
        await session.commit()

    token = await _authenticate(client, "superadmin@example.com", superadmin_password)
    headers = {"Authorization": f"Bearer {token}"}

    create_payload = {
        "account_id": str(account_id),
        "name": "Downtown",
        "timezone": "UTC",
        "city": "Cedar Rapids",
    }
    create_resp = await client.post("/api/v1/locations", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    location_id = create_resp.json()["id"]

    list_resp = await client.get(
        f"/api/v1/locations?account_id={account_id}",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert any(item["id"] == location_id for item in list_resp.json())

    update_resp = await client.patch(
        f"/api/v1/locations/{location_id}",
        json={"name": "Downtown Plus"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Downtown Plus"

    delete_resp = await client.delete(f"/api/v1/locations/{location_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_deleted = await client.get(f"/api/v1/locations/{location_id}", headers=headers)
    assert get_deleted.status_code == 404


async def test_location_admin_scope(app_context: dict[str, object], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_id = app_context["account_id"]

    sessionmaker = get_sessionmaker(db_url)
    admin_password = "AdminPass1!"
    async with sessionmaker() as session:
        admin_user = User(
            account_id=account_id,
            email="admin@example.com",
            hashed_password=get_password_hash(admin_password),
            first_name="Avery",
            last_name="Admin",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(admin_user)

        other_account = Account(name="Other Resort", slug=f"other-{uuid.uuid4().hex[:6]}")
        session.add(other_account)
        await session.flush()

        other_location = Location(
            account_id=other_account.id,
            name="Iowa City",
            timezone="UTC",
        )
        session.add(other_location)
        await session.commit()

    token = await _authenticate(client, "admin@example.com", admin_password)
    headers = {"Authorization": f"Bearer {token}"}

    list_resp = await client.get("/api/v1/locations", headers=headers)
    assert list_resp.status_code == 200
    assert all(item["account_id"] == str(account_id) for item in list_resp.json())

    create_other = await client.post(
        "/api/v1/locations",
        json={
            "account_id": str(other_account.id),
            "name": "Unauthorized",
            "timezone": "UTC",
        },
        headers=headers,
    )
    assert create_other.status_code == 400

    get_other = await client.get(f"/api/v1/locations/{other_location.id}", headers=headers)
    assert get_other.status_code == 404


async def test_location_manager_forbidden(app_context: dict[str, object]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    token = await _authenticate(client, app_context["manager_email"], app_context["manager_password"])  # type: ignore[arg-type]
    headers = {"Authorization": f"Bearer {token}"}

    list_resp = await client.get("/api/v1/locations", headers=headers)
    assert list_resp.status_code == 403
