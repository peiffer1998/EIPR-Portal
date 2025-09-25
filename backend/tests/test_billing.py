"""Billing API integration tests."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient

from app.api import deps
from app.db.session import get_sessionmaker
from app.integrations import PaymentIntent
from app.main import app
from app.models import (
    Deposit,
    DepositStatus,
    PriceRule,
    PriceRuleType,
    Promotion,
    PromotionKind,
)

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
) -> dict[str, str]:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Bill",
            "last_name": "Payer",
            "email": f"bill.payer-{uuid.uuid4().hex[:6]}@example.com",
            "password": "StrongPass1!",
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
            "name": "BillingDog",
            "pet_type": "dog",
        },
        headers=headers,
    )
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]

    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    end_at = start_at + timedelta(days=2)
    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={
            "pet_id": pet_id,
            "location_id": location_id,
            "reservation_type": "boarding",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "base_rate": "200.00",
        },
        headers=headers,
    )
    assert reservation_resp.status_code == 201
    reservation_id = reservation_resp.json()["id"]
    return {
        "owner_id": owner_id,
        "pet_id": pet_id,
        "reservation_id": reservation_id,
    }


@pytest.fixture()
async def stripe_stub():
    class _StubStripeClient:
        def __init__(self) -> None:
            self.invoice_id: uuid.UUID | None = None
            self.account_id: uuid.UUID | None = None

        def create_payment_intent(
            self, *, amount: Decimal, invoice_id: uuid.UUID, metadata: dict[str, Any]
        ) -> PaymentIntent:
            self.invoice_id = invoice_id
            self.account_id = uuid.UUID(metadata["account_id"])
            return PaymentIntent(
                id="pi_test_123",
                client_secret="secret",
                status="requires_confirmation",
                metadata={
                    "invoice_id": str(invoice_id),
                    "account_id": metadata["account_id"],
                },
            )

        def confirm_payment_intent(self, payment_intent_id: str) -> PaymentIntent:
            return PaymentIntent(
                id=payment_intent_id,
                client_secret="secret",
                status="succeeded",
                metadata={
                    "invoice_id": str(self.invoice_id),
                    "account_id": str(self.account_id),
                },
            )

        def construct_event(self, payload: bytes, signature: str) -> dict[str, Any]:
            return {
                "type": "payment_intent.succeeded",
                "data": {
                    "object": {
                        "metadata": {
                            "invoice_id": str(self.invoice_id),
                            "account_id": str(self.account_id),
                        }
                    }
                },
            }

    stub = _StubStripeClient()
    app.dependency_overrides[deps.get_stripe_client] = lambda: stub
    yield stub
    app.dependency_overrides.pop(deps.get_stripe_client, None)


async def test_invoice_totals_and_promotion(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    token = await _authenticate(
        client, app_context["manager_email"], app_context["manager_password"]
    )
    headers = {"Authorization": f"Bearer {token}"}
    reservation_data = await _create_owner_pet_reservation(
        client, headers, str(app_context["location_id"])
    )

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        session.add(
            PriceRule(
                account_id=app_context["account_id"],
                rule_type=PriceRuleType.PEAK_DATE,
                params={
                    "start_date": datetime.now(timezone.utc).date().isoformat(),
                    "end_date": (datetime.now(timezone.utc) + timedelta(days=10))
                    .date()
                    .isoformat(),
                    "amount": "25.00",
                },
            )
        )
        session.add(
            Promotion(
                account_id=app_context["account_id"],
                code="SPRING10",
                kind=PromotionKind.PERCENT,
                value=Decimal("10"),
                starts_on=datetime.now(timezone.utc).date() - timedelta(days=1),
                ends_on=datetime.now(timezone.utc).date() + timedelta(days=10),
                active=True,
            )
        )
        await session.commit()

    create_resp = await client.post(
        f"/api/v1/invoices/{reservation_data['reservation_id']}/create",
        headers=headers,
    )
    assert create_resp.status_code == 200
    invoice = create_resp.json()
    assert invoice["subtotal"] == "225.00"
    assert invoice["discount_total"] == "0"
    invoice_id = invoice["id"]

    apply_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/apply-promo",
        json={"code": "SPRING10"},
        headers=headers,
    )
    assert apply_resp.status_code == 200
    body = apply_resp.json()
    assert body["discount_total"] == "22.50"
    assert body["total_amount"] == "202.50"


async def test_deposit_payment_and_export_flow(
    app_context: dict[str, Any],
    db_url: str,
    tmp_path: Any,
    stripe_stub: Any,
) -> None:
    os.environ["QBO_EXPORT_DIR"] = str(tmp_path)
    deps.get_settings.cache_clear()  # type: ignore[attr-defined]

    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    token = await _authenticate(
        client, app_context["manager_email"], app_context["manager_password"]
    )
    headers = {"Authorization": f"Bearer {token}"}
    reservation_data = await _create_owner_pet_reservation(
        client, headers, str(app_context["location_id"])
    )

    create_resp = await client.post(
        f"/api/v1/invoices/{reservation_data['reservation_id']}/create",
        headers=headers,
    )
    assert create_resp.status_code == 200
    invoice_id = create_resp.json()["id"]

    hold_resp = await client.post(
        f"/api/v1/reservations/{reservation_data['reservation_id']}/hold-deposit",
        json={"owner_id": reservation_data["owner_id"], "amount": "50.00"},
        headers=headers,
    )
    assert hold_resp.status_code == 200
    deposit_id = hold_resp.json()["id"]
    assert hold_resp.json()["status"] == "held"

    intent_resp = await client.post(
        "/api/v1/payments/create-intent",
        json={"invoice_id": invoice_id, "amount": "200.00"},
        headers=headers,
    )
    assert intent_resp.status_code == 200
    intent_id = intent_resp.json()["payment_intent_id"]

    confirm_resp = await client.post(
        "/api/v1/payments/confirm",
        json={"payment_intent_id": intent_id},
        headers=headers,
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "paid"

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        deposit = await session.get(Deposit, uuid.UUID(deposit_id))
        assert deposit is not None
        assert deposit.status == DepositStatus.CONSUMED

    today = datetime.now(timezone.utc).date()
    export_resp = await client.get(
        "/api/v1/reports/exports/sales-receipt",
        params={"date": today.isoformat()},
        headers=headers,
    )
    assert export_resp.status_code == 200
    export_path = export_resp.json()["export_path"]
    assert export_resp.json()["invoices_exported"] >= 0

    with open(export_path, "r", encoding="utf-8") as handle:
        header = handle.readline().strip()
    assert header.split(",")[0] == "invoice_id"
