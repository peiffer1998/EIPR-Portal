"""Self-service authentication tests."""

from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models.audit_event import AuditEvent

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


async def test_pet_parent_registration_and_login(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_slug = app_context["account_slug"]

    payload = {
        "account_slug": account_slug,
        "email": "parent1@example.com",
        "password": "RegisterMe1!",
        "first_name": "Pat",
        "last_name": "Parent",
    }
    register_resp = await client.post("/api/v1/auth/register", json=payload)
    assert register_resp.status_code == 201
    body = register_resp.json()
    assert body["owner"]["user"]["email"] == payload["email"]
    assert "access_token" in body["token"]

    login_resp = await client.post(
        "/api/v1/auth/token",
        data={"username": payload["email"], "password": payload["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["access_token"]

    register_events = await _fetch_events(db_url, "auth.register.pet_parent")
    assert any(
        evt.payload and evt.payload.get("email") == payload["email"]
        for evt in register_events
    )

    login_events = await _fetch_events(db_url, "auth.login")
    assert any(
        evt.payload and evt.payload.get("email") == payload["email"]
        for evt in login_events
    )


async def test_password_reset_flow(app_context: dict[str, Any], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_slug = app_context["account_slug"]
    email = "reset.me@example.com"

    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "account_slug": account_slug,
            "email": email,
            "password": "InitialPass1!",
            "first_name": "Riley",
            "last_name": "Reset",
        },
    )
    assert register_resp.status_code == 201

    request_resp = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": email},
    )
    assert request_resp.status_code == 200
    token_payload = request_resp.json()
    assert token_payload["reset_token"] is not None

    confirm_resp = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token_payload["reset_token"], "new_password": "NewPass2!"},
    )
    assert confirm_resp.status_code == 204

    request_events = await _fetch_events(db_url, "auth.password_reset.requested")
    assert any(
        evt.payload and evt.payload.get("email") == email for evt in request_events
    )

    completed_events = await _fetch_events(db_url, "auth.password_reset.completed")
    assert any(
        evt.payload and evt.payload.get("email") == email for evt in completed_events
    )

    login_resp = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": "NewPass2!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200

    login_events = await _fetch_events(db_url, "auth.login")
    assert any(
        evt.payload and evt.payload.get("email") == email for evt in login_events
    )


async def test_owner_self_service_reservation(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_slug = app_context["account_slug"]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "account_slug": account_slug,
            "email": "owner.pet@example.com",
            "password": "OwnerPass1!",
            "first_name": "Olivia",
            "last_name": "Owner",
        },
    )
    assert register_resp.status_code == 201
    owner_body = register_resp.json()["owner"]
    owner_id = owner_body["id"]
    owner_token = register_resp.json()["token"]["access_token"]

    manager_token = await _authenticate(client, manager_email, manager_password)
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    pet_resp = await client.post(
        "/api/v1/pets",
        json={
            "owner_id": owner_id,
            "home_location_id": location_id,
            "name": "Buddy",
            "pet_type": "dog",
        },
        headers=manager_headers,
    )
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    start_at = datetime.now(timezone.utc) + timedelta(days=3)
    end_at = start_at + timedelta(days=2)
    reservation_resp = await client.post(
        f"/api/v1/owners/{owner_id}/reservations",
        json={
            "pet_id": pet_id,
            "location_id": location_id,
            "reservation_type": "boarding",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
        },
        headers=owner_headers,
    )
    assert reservation_resp.status_code == 201
    reservation_body = reservation_resp.json()
    assert reservation_body["status"] == "requested"
    assert reservation_body["pet_id"] == pet_id
