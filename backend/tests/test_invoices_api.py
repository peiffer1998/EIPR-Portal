"""API tests for invoice endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient

from app.db.session import get_sessionmaker
from app.models import PriceRule, PriceRuleType, Promotion, PromotionKind

pytestmark = pytest.mark.asyncio


async def _authenticate(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


async def _create_owner_pet_reservation(
    client: AsyncClient,
    headers: dict[str, str],
    location_id: str,
    *,
    owner_email: str,
    base_rate: str,
) -> tuple[str, datetime]:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Harper",
            "last_name": "Client",
            "email": owner_email,
            "password": "StrongPass9!",
        },
        headers=headers,
    )
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["id"]

    pet_resp = await client.post(
        "/api/v1/pets",
        json={
            "owner_id": owner_id,
            "home_location_id": location_id,
            "name": "InvoiceDog",
            "pet_type": "dog",
        },
        headers=headers,
    )
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]

    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={
            "pet_id": pet_id,
            "location_id": location_id,
            "reservation_type": "boarding",
            "start_at": start_at.isoformat(),
            "end_at": (start_at + timedelta(days=2)).isoformat(),
            "base_rate": base_rate,
        },
        headers=headers,
    )
    assert reservation_resp.status_code == 201
    reservation_id = reservation_resp.json()["id"]
    return reservation_id, start_at


async def test_invoice_creation_and_promotion(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    account_id = app_context["account_id"]
    location_id = str(app_context["location_id"])

    manager_token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {manager_token}"}

    reservation_id, start_at = await _create_owner_pet_reservation(
        client,
        headers,
        location_id,
        owner_email="invoice-owner@example.com",
        base_rate="150.00",
    )

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        session.add_all(
            [
                PriceRule(
                    account_id=account_id,
                    rule_type=PriceRuleType.PEAK_DATE,
                    params={"dates": [start_at.date().isoformat()], "amount": "20.00"},
                ),
                Promotion(
                    account_id=account_id,
                    code="WELCOME10",
                    kind=PromotionKind.PERCENT,
                    value=Decimal("10"),
                    active=True,
                ),
            ]
        )
        await session.commit()

    create_resp = await client.post(
        "/api/v1/invoices/from-reservation",
        json={"reservation_id": reservation_id},
        headers=headers,
    )
    assert create_resp.status_code == 201
    invoice_body = create_resp.json()
    assert invoice_body["subtotal"] == "170.00"
    invoice_id = invoice_body["id"]

    promo_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/apply-promo",
        json={"code": "WELCOME10"},
        headers=headers,
    )
    assert promo_resp.status_code == 200
    totals = promo_resp.json()
    assert totals["discount_total"] == "17.00"
    assert totals["total"] == "153.00"
