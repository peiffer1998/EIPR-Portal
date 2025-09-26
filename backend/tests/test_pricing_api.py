"""API tests for pricing endpoints."""

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


async def _create_owner_and_pet(
    client: AsyncClient,
    headers: dict[str, str],
    location_id: str,
    *,
    email: str,
) -> tuple[str, str]:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Jordan",
            "last_name": "Client",
            "email": email,
            "password": "Str0ngPass!",
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
            "name": "Comet",
            "pet_type": "dog",
        },
        headers=headers,
    )
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]
    return owner_id, pet_id


async def _create_reservation(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    pet_id: str,
    location_id: str,
    base_rate: str,
) -> tuple[str, datetime]:
    start_at = datetime.now(timezone.utc) + timedelta(days=2)
    response = await client.post(
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
    assert response.status_code == 201
    return response.json()["id"], start_at


async def test_pricing_quote_with_promotion(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    account_id = app_context["account_id"]
    location_id = str(app_context["location_id"])

    manager_token = await _authenticate(client, manager_email, manager_password)
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    owner_email = "pricing-owner@example.com"
    _, pet_id = await _create_owner_and_pet(
        client,
        manager_headers,
        location_id,
        email=owner_email,
    )
    reservation_id, start_at = await _create_reservation(
        client,
        manager_headers,
        pet_id=pet_id,
        location_id=location_id,
        base_rate="100.00",
    )

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        session.add_all(
            [
                PriceRule(
                    account_id=account_id,
                    rule_type=PriceRuleType.PEAK_DATE,
                    params={"dates": [start_at.date().isoformat()], "amount": "15.00"},
                ),
                PriceRule(
                    account_id=account_id,
                    rule_type=PriceRuleType.LATE_CHECKOUT,
                    params={"hour": 10, "amount": "20.00"},
                ),
                Promotion(
                    account_id=account_id,
                    code="SPRING10",
                    kind=PromotionKind.PERCENT,
                    value=Decimal("10"),
                    active=True,
                ),
            ]
        )
        await session.commit()

    quote_resp = await client.post(
        "/api/v1/pricing/quote",
        json={"reservation_id": reservation_id, "promotion_code": "SPRING10"},
        headers=manager_headers,
    )
    assert quote_resp.status_code == 200
    body = quote_resp.json()
    assert body["reservation_id"] == reservation_id
    assert any(item["description"] == "Peak date surcharge" for item in body["items"])
    assert body["discount_total"] != "0.00"

    owner_login = await client.post(
        "/api/v1/auth/token",
        data={"username": owner_email, "password": "Str0ngPass!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert owner_login.status_code == 200
    owner_token = owner_login.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    owner_quote = await client.post(
        "/api/v1/pricing/quote",
        json={"reservation_id": reservation_id},
        headers=owner_headers,
    )
    assert owner_quote.status_code == 200
