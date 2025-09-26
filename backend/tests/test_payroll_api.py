"""Integration tests for payroll and tip APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import chain, repeat
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models import TipPolicy, User, UserRole, UserStatus
from app.services import timeclock_service

pytestmark = pytest.mark.asyncio


async def _authenticate(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _ensure_secondary_staff(app_context: dict[str, Any]) -> User:
    sessionmaker = app_context["sessionmaker"]
    async with sessionmaker() as session:
        result = await session.execute(
            select(User).where(
                User.email == "staff.secondary@example.com",
                User.account_id == app_context["account_id"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        staff = User(
            account_id=app_context["account_id"],
            email="staff.secondary@example.com",
            hashed_password="x",
            first_name="Sky",
            last_name="Stylist",
            role=UserRole.STAFF,
            status=UserStatus.ACTIVE,
        )
        session.add(staff)
        await session.commit()
        await session.refresh(staff)
        return staff


async def test_tip_endpoint_pooled_by_hours(
    app_context: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    location_id = str(app_context["location_id"])
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    manager_user: User
    sessionmaker = app_context["sessionmaker"]
    async with sessionmaker() as session:
        manager_user = (
            await session.execute(select(User).where(User.email == manager_email))
        ).scalar_one()

    secondary_staff = await _ensure_secondary_staff(app_context)

    start_primary = datetime(2025, 6, 1, 9, 0, tzinfo=UTC)
    end_primary = start_primary + timedelta(hours=2)

    times_iter = chain([start_primary, end_primary], repeat(end_primary))
    real_datetime = timeclock_service.datetime

    class FakeDateTime:
        @staticmethod
        def now(tz: Any = None) -> datetime:
            return next(times_iter)

        @staticmethod
        def fromtimestamp(ts: float, tz: Any = None) -> datetime:
            return real_datetime.fromtimestamp(ts, tz=tz)

    monkeypatch.setattr(timeclock_service, "datetime", FakeDateTime)

    punch_in_resp = await client.post(
        "/api/v1/timeclock/punch-in",
        params={"location_id": location_id},
        headers=headers,
    )
    assert punch_in_resp.status_code == 201

    punch_out_resp = await client.post(
        "/api/v1/timeclock/punch-out",
        headers=headers,
    )
    assert punch_out_resp.status_code == 200
    punch_payload = punch_out_resp.json()
    assert punch_payload["minutes_worked"] == 120

    start_secondary = datetime(2025, 6, 1, 8, 0, tzinfo=UTC)
    end_secondary = start_secondary + timedelta(hours=4)
    async with sessionmaker() as session:
        await timeclock_service.punch_in(
            session,
            account_id=app_context["account_id"],
            location_id=app_context["location_id"],
            user_id=secondary_staff.id,
            at=start_secondary,
            source="test",
        )
        await timeclock_service.punch_out(
            session,
            account_id=app_context["account_id"],
            user_id=secondary_staff.id,
            at=end_secondary,
        )

    tip_resp = await client.post(
        "/api/v1/tips",
        json={
            "location_id": location_id,
            "date": start_primary.date().isoformat(),
            "amount": "30.00",
            "policy": TipPolicy.POOLED_BY_HOURS.value,
        },
        headers=headers,
    )
    assert tip_resp.status_code == 201, tip_resp.text
    tip_payload = tip_resp.json()

    shares = {share["user_id"]: share["amount"] for share in tip_payload["shares"]}
    assert str(manager_user.id) in shares
    assert str(secondary_staff.id) in shares
    assert shares[str(manager_user.id)] == "10.00"
    assert shares[str(secondary_staff.id)] == "20.00"

    tips_list_resp = await client.get("/api/v1/tips", headers=headers)
    assert tips_list_resp.status_code == 200
    assert tips_list_resp.json()[0]["shares"] == tip_payload["shares"]
