"""Staff role management tests."""

from __future__ import annotations

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


async def test_superadmin_can_invite_and_accept_staff(
    app_context: dict[str, Any],
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    superadmin_email = app_context["superadmin_email"]
    superadmin_password = app_context["superadmin_password"]

    token = await _authenticate(client, superadmin_email, superadmin_password)
    headers = {"Authorization": f"Bearer {token}"}

    invite_resp = await client.post(
        "/api/v1/users/invitations",
        json={
            "email": "new.staff@example.com",
            "first_name": "Taylor",
            "last_name": "Trainer",
            "role": "staff",
            "expires_in_hours": 48,
        },
        headers=headers,
    )
    assert invite_resp.status_code == 201
    invite_body = invite_resp.json()
    invite_token = invite_body["invite_token"]
    assert invite_token

    accept_resp = await client.post(
        "/api/v1/auth/invitations/accept",
        json={
            "token": invite_token,
            "password": "StaffPass1!",
            "first_name": "Taylor",
            "last_name": "Trainer",
            "phone_number": "3195550000",
        },
    )
    assert accept_resp.status_code == 200
    accept_body = accept_resp.json()
    assert accept_body["user"]["email"] == "new.staff@example.com"
    assert accept_body["user"]["role"] == "staff"
    assert accept_body["token"]["access_token"]

    # New staff member can authenticate with chosen password
    login_resp = await client.post(
        "/api/v1/auth/token",
        data={"username": "new.staff@example.com", "password": "StaffPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200


async def test_superadmin_can_change_user_role(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    superadmin_email = app_context["superadmin_email"]
    superadmin_password = app_context["superadmin_password"]

    token = await _authenticate(client, superadmin_email, superadmin_password)
    headers = {"Authorization": f"Bearer {token}"}

    users_resp = await client.get("/api/v1/users", headers=headers)
    assert users_resp.status_code == 200
    users = users_resp.json()
    manager = next(
        user for user in users if user["email"] == app_context["manager_email"]
    )

    update_resp = await client.patch(
        f"/api/v1/users/{manager['id']}",
        json={"role": "admin"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["role"] == "admin"


async def test_manager_cannot_modify_superadmin(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    superadmin_email = app_context["superadmin_email"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    users_resp = await client.get("/api/v1/users", headers=headers)
    assert users_resp.status_code == 200
    users = users_resp.json()
    superadmin = next(user for user in users if user["email"] == superadmin_email)

    update_resp = await client.patch(
        f"/api/v1/users/{superadmin['id']}",
        json={"role": "manager"},
        headers=headers,
    )
    assert update_resp.status_code == 403
