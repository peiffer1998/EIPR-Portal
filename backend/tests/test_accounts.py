"""Account administration tests."""

from __future__ import annotations

from typing import Any
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import Account, AuditEvent, User, UserRole, UserStatus

pytestmark = pytest.mark.asyncio


async def _fetch_events(db_url: str, event_type: str) -> list[AuditEvent]:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        result = await session.execute(
            select(AuditEvent).where(AuditEvent.event_type == event_type)
        )
        events = result.scalars().all()
        return list(events)


async def _authenticate(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def test_account_crud_superadmin(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]

    sessionmaker = get_sessionmaker(db_url)
    superadmin_password = "SuperPass1!"
    async with sessionmaker() as session:
        superadmin = User(
            account_id=app_context["account_id"],
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

    create_payload = {"name": "North Resort", "slug": f"north-{uuid.uuid4().hex[:6]}"}
    create_resp = await client.post(
        "/api/v1/accounts", json=create_payload, headers=headers
    )
    assert create_resp.status_code == 201
    account_id = create_resp.json()["id"]

    created_events = await _fetch_events(db_url, "account.created")
    assert any(
        evt.payload and evt.payload.get("slug") == create_payload["slug"]
        for evt in created_events
    )

    list_resp = await client.get("/api/v1/accounts", headers=headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == account_id for item in list_resp.json())

    update_resp = await client.patch(
        f"/api/v1/accounts/{account_id}",
        json={"name": "North Resort Updated"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "North Resort Updated"

    updated_events = await _fetch_events(db_url, "account.updated")
    assert any(
        evt.payload and evt.payload.get("account_id") == account_id
        for evt in updated_events
    )

    delete_resp = await client.delete(f"/api/v1/accounts/{account_id}", headers=headers)
    assert delete_resp.status_code == 204

    deleted_events = await _fetch_events(db_url, "account.deleted")
    assert any(
        evt.payload and evt.payload.get("account_id") == account_id
        for evt in deleted_events
    )

    get_deleted = await client.get(f"/api/v1/accounts/{account_id}", headers=headers)
    assert get_deleted.status_code == 404


async def test_account_admin_permissions(
    app_context: dict[str, Any], db_url: str
) -> None:
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

        other_account = Account(
            name="Other Resort", slug=f"other-{uuid.uuid4().hex[:6]}"
        )
        session.add(other_account)
        await session.commit()

    token = await _authenticate(client, "admin@example.com", admin_password)
    headers = {"Authorization": f"Bearer {token}"}

    list_resp = await client.get("/api/v1/accounts", headers=headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1
    assert data[0]["id"] == str(account_id)

    get_resp = await client.get(f"/api/v1/accounts/{account_id}", headers=headers)
    assert get_resp.status_code == 200

    get_other = await client.get(
        f"/api/v1/accounts/{other_account.id}", headers=headers
    )
    assert get_other.status_code == 404

    update_resp = await client.patch(
        f"/api/v1/accounts/{account_id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Name"

    create_attempt = await client.post(
        "/api/v1/accounts",
        json={"name": "New Resort", "slug": "new-resort"},
        headers=headers,
    )
    assert create_attempt.status_code == 403


async def test_account_manager_forbidden(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    token = await _authenticate(
        client, app_context["manager_email"], app_context["manager_password"]
    )  # type: ignore[arg-type]
    headers = {"Authorization": f"Bearer {token}"}

    list_resp = await client.get("/api/v1/accounts", headers=headers)
    assert list_resp.status_code == 403
