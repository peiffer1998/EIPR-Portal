"""Portal store API tests."""

from __future__ import annotations

import datetime
import os
import uuid
from decimal import Decimal
from typing import Any, cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api import deps
from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.models import ReservationStatus, ReservationType
from app.models.pet import Pet, PetType
from app.services import invoice_service, pet_service, reservation_service

pytestmark = pytest.mark.asyncio


async def _portal_auth(
    client: AsyncClient, email: str, password: str
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/portal/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_portal_store_flow(app_context: dict[str, Any], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_id = cast(uuid.UUID, app_context["account_id"])
    account_slug = cast(str, app_context["account_slug"])
    location_id = cast(uuid.UUID, app_context["location_id"])

    os.environ["PORTAL_ACCOUNT_SLUG"] = account_slug
    get_settings.cache_clear()
    get_settings()
    deps._build_s3_client.cache_clear()

    manager_credentials = {
        "username": cast(str, app_context["manager_email"]),
        "password": cast(str, app_context["manager_password"]),
    }
    manager_headers_resp = await client.post(
        "/api/v1/auth/token",
        data=manager_credentials,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert manager_headers_resp.status_code == 200
    manager_token = manager_headers_resp.json()["access_token"]
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    package_resp = await client.post(
        "/api/v1/store/package-types",
        json={
            "name": "Portal Daycare",
            "applies_to": "daycare",
            "credits_per_package": 4,
            "price": "160.00",
            "active": True,
        },
        headers=manager_headers,
    )
    assert package_resp.status_code == 201
    package_type_id = package_resp.json()["id"]

    owner_email = f"portal+{uuid.uuid4().hex[:6]}@example.com"
    owner_password = "PortalStrong1!"

    register_resp = await client.post(
        "/api/v1/portal/register_owner",
        json={
            "first_name": "Morgan",
            "last_name": "PortalStore",
            "email": owner_email,
            "password": owner_password,
            "account_slug": account_slug,
        },
    )
    assert register_resp.status_code == 201
    register_body = register_resp.json()
    owner_id = uuid.UUID(register_body["owner"]["id"])
    portal_headers = {"Authorization": f"Bearer {register_body['access_token']}"}

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        await pet_service.create_pet(
            session,
            account_id=account_id,
            owner_id=owner_id,
            home_location_id=location_id,
            name="PortalDog",
            pet_type=PetType.DOG,
            breed=None,
            color=None,
            date_of_birth=None,
            notes=None,
        )

    balances_resp = await client.get(
        "/api/v1/portal/store/balances",
        headers=portal_headers,
    )
    assert balances_resp.status_code == 200, balances_resp.text
    assert balances_resp.json()["store_credit"]["balance"] == "0.00"

    package_buy_resp = await client.post(
        "/api/v1/portal/store/packages/buy",
        json={"package_type_id": package_type_id, "quantity": 1},
        headers=portal_headers,
    )
    assert package_buy_resp.status_code == 201
    package_body = package_buy_resp.json()
    assert package_body["client_secret"]
    uuid.UUID(package_body["invoice_id"])

    gift_buy_resp = await client.post(
        "/api/v1/portal/store/gift-certificates/buy",
        json={"amount": "40.00"},
        headers=portal_headers,
    )
    assert gift_buy_resp.status_code == 201
    gift_body = gift_buy_resp.json()
    gift_code = gift_body["gift_certificate_code"]
    assert gift_code

    redeem_resp = await client.post(
        "/api/v1/portal/store/gift-certificates/redeem",
        json={"code": gift_code},
        headers=portal_headers,
    )
    assert redeem_resp.status_code == 200
    redeem_balance = Decimal(redeem_resp.json()["store_credit"]["balance"])
    assert redeem_balance == Decimal("40.00")

    async with sessionmaker() as session:
        owner_pet = await session.execute(
            select(Pet.id).where(Pet.owner_id == owner_id)
        )
        pet_row = owner_pet.first()
        assert pet_row is not None
        pet_id = pet_row[0]
        start_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3)
        end_at = start_at + datetime.timedelta(days=2)
        reservation = await reservation_service.create_reservation(
            session,
            account_id=account_id,
            pet_id=pet_id,
            location_id=location_id,
            reservation_type=ReservationType.BOARDING,
            start_at=start_at,
            end_at=end_at,
            base_rate=Decimal("80.00"),
            status=ReservationStatus.CONFIRMED,
        )
        await session.commit()
        invoice_to_pay = await invoice_service.create_from_reservation(
            session,
            reservation_id=reservation.id,
            account_id=account_id,
        )

    apply_credit_resp = await client.post(
        f"/api/v1/portal/invoices/{invoice_to_pay}/apply-store-credit",
        json={"amount": "100.00"},
        headers=portal_headers,
    )
    assert apply_credit_resp.status_code == 200
    new_balance = Decimal(apply_credit_resp.json()["store_credit"]["balance"])
    assert new_balance <= Decimal("40.00")
