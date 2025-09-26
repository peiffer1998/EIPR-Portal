# Billing API tests.
from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import Account, Location, User, UserRole, UserStatus

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
) -> tuple[str, str]:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Bill",
            "last_name": "Payer",
            "email": "bill.payer@example.com",
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
    return reservation_id, pet_id


async def test_invoice_lifecycle(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    reservation_id, _ = await _create_owner_pet_reservation(
        client, headers, location_id
    )

    invoice_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/invoice",
        headers=headers,
    )
    assert invoice_resp.status_code == 200
    invoice = invoice_resp.json()
    invoice_id = invoice["id"]
    assert invoice["status"] == "pending"
    assert len(invoice["items"]) == 1
    line = invoice["items"][0]
    assert line["description"] == "Base rate"
    assert line["amount"] == "200.00"
    assert invoice["subtotal"] == "200.00"
    assert invoice["total"] == "200.00"

    list_resp = await client.get("/api/v1/invoices", headers=headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == invoice_id for item in list_resp.json())

    add_item_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/items",
        json={"description": "Late checkout", "amount": "25.00"},
        headers=headers,
    )
    assert add_item_resp.status_code == 200
    body = add_item_resp.json()
    assert len(body["items"]) == 2
    assert body["subtotal"] == "225.00"
    assert body["total"] == "225.00"
    assert body["total_amount"] == "225.00"

    pay_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/pay",
        json={"amount": "225.00"},
        headers=headers,
    )
    assert pay_resp.status_code == 200
    paid_invoice = pay_resp.json()
    assert paid_invoice["status"] == "paid"
    assert paid_invoice["paid_at"] is not None

    duplicate_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/invoice",
        headers=headers,
    )
    assert duplicate_resp.status_code == 400


async def test_invoice_account_isolation(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}
    reservation_id, _ = await _create_owner_pet_reservation(
        client, headers, location_id
    )

    invoice_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/invoice",
        headers=headers,
    )
    assert invoice_resp.status_code == 200
    invoice_id = invoice_resp.json()["id"]

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        other_account = Account(
            name="Other Resort", slug=f"other-{uuid.uuid4().hex[:6]}"
        )
        session.add(other_account)
        await session.flush()

        session.add(
            Location(
                account_id=other_account.id,
                name="Iowa City",
                timezone="UTC",
            )
        )

        other_password = "Passw0rd!"
        other_manager = User(
            account_id=other_account.id,
            email="other.billing@example.com",
            hashed_password=get_password_hash(other_password),
            first_name="Other",
            last_name="Billing",
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
        )
        session.add(other_manager)
        await session.commit()

    other_token = await _authenticate(
        client, "other.billing@example.com", other_password
    )
    other_headers = {"Authorization": f"Bearer {other_token}"}

    forbidden_resp = await client.get(
        f"/api/v1/invoices/{invoice_id}",
        headers=other_headers,
    )
    assert forbidden_resp.status_code == 404
