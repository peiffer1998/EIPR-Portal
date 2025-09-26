"""Tests for the customer portal endpoints."""

from __future__ import annotations

import datetime
import os
import uuid
from decimal import Decimal

import pytest

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from sqlalchemy import select
from app.models.pet import PetType
from app.models.account import Account
from app.models.reservation import ReservationStatus, ReservationType
from app.services import invoice_service, pet_service, reservation_service

pytestmark = pytest.mark.asyncio


async def _auth_headers(client, email: str, password: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/portal/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_portal_owner_flow(app_context, db_url: str) -> None:
    client = app_context["client"]
    account_slug = app_context["account_slug"]

    os.environ["PORTAL_ACCOUNT_SLUG"] = account_slug
    get_settings.cache_clear()
    get_settings()

    email = f"owner+{uuid.uuid4().hex[:6]}@example.com"
    password = "Secure123!"

    register = await client.post(
        "/api/v1/portal/register_owner",
        json={
            "first_name": "Jamie",
            "last_name": "Portal",
            "email": email,
            "password": password,
            "phone_number": "555-0000",
            "account_slug": account_slug,
        },
    )
    assert register.status_code == 201, register.json()
    payload = register.json()
    owner_id = uuid.UUID(payload["owner"]["id"])
    token = payload["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        existing = await session.execute(select(Account.slug))
        assert account_slug in {row[0] for row in existing}
        await pet_service.create_pet(
            session,
            account_id=app_context["account_id"],
            owner_id=owner_id,
            home_location_id=app_context["location_id"],
            name="Rex",
            pet_type=PetType.DOG,
            breed=None,
            color=None,
            date_of_birth=None,
            notes=None,
        )

    me = await client.get("/api/v1/portal/me", headers=headers)
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["owner"]["id"] == str(owner_id)
    assert len(me_body["pets"]) == 1

    pet_id = uuid.UUID(me_body["pets"][0]["id"])
    start_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2)
    end_at = start_at + datetime.timedelta(days=2)

    request_resp = await client.post(
        "/api/v1/portal/reservations/request",
        headers=headers,
        json={
            "pet_id": str(pet_id),
            "reservation_type": ReservationType.BOARDING.value,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "notes": "Boarding request",
        },
    )
    assert request_resp.status_code == 201
    reservation_id = uuid.UUID(request_resp.json()["id"])

    cancel_resp = await client.post(
        f"/api/v1/portal/reservations/{reservation_id}/cancel",
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == ReservationStatus.CANCELED.value

    async with sessionmaker() as session:
        reservation = await reservation_service.create_reservation(
            session,
            account_id=app_context["account_id"],
            pet_id=pet_id,
            location_id=app_context["location_id"],
            reservation_type=ReservationType.BOARDING,
            start_at=start_at,
            end_at=end_at,
            base_rate=Decimal("0"),
            status=ReservationStatus.CONFIRMED,
        )
        invoice_id = await invoice_service.create_from_reservation(
            session,
            reservation_id=reservation.id,
            account_id=app_context["account_id"],
        )

    invoice_resp = await client.post(
        "/api/v1/portal/payments/create-intent",
        headers=headers,
        json={"invoice_id": str(invoice_id)},
    )
    assert invoice_resp.status_code == 200
    invoice_body = invoice_resp.json()
    assert invoice_body["invoice_id"] == str(invoice_id)
    assert invoice_body["client_secret"]

    login_headers = await _auth_headers(client, email, password)
    me_again = await client.get("/api/v1/portal/me", headers=login_headers)
    assert me_again.status_code == 200
