"""Tests for the runs (lodging) API."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from app.db.session import get_sessionmaker
from app.models.lodging import LodgingType

pytestmark = pytest.mark.asyncio


async def _auth_manager(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def test_runs_fallback(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    token = await _auth_manager(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/runs", headers=headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 2
    assert payload[0]["id"] == "ROOM"


async def test_runs_with_lodging_types(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    account_id = app_context["account_id"]
    location_id = app_context["location_id"]

    token = await _auth_manager(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        run = LodgingType(
            account_id=account_id,
            location_id=location_id,
            name="Deluxe Suite",
        )
        session.add(run)
        await session.commit()
        run_id = str(run.id)

    resp = await client.get("/api/v1/runs", headers=headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert any(
        item["id"] == run_id and item["name"] == "Deluxe Suite" for item in payload
    )

    other_location = str(uuid.uuid4())
    filtered = await client.get(
        "/api/v1/runs",
        headers=headers,
        params={"location_id": other_location},
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 2
