"""API tests for staff store endpoints."""

from __future__ import annotations

from typing import Any
from decimal import Decimal
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _auth_manager(
    client: AsyncClient, email: str, password: str
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_owner_and_pet(
    client: AsyncClient,
    headers: dict[str, str],
    location_id: str,
) -> tuple[str, str]:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Taylor",
            "last_name": "Store",
            "email": "taylor.store@example.com",
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
            "name": "StoreCat",
            "pet_type": "cat",
        },
        headers=headers,
    )
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]
    return owner_id, pet_id


async def test_store_staff_flow(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    headers = await _auth_manager(client, manager_email, manager_password)

    package_resp = await client.post(
        "/api/v1/store/package-types",
        json={
            "name": "Boarding 3 Pack",
            "applies_to": "boarding",
            "credits_per_package": 3,
            "price": "180.00",
            "active": True,
        },
        headers=headers,
    )
    assert package_resp.status_code == 201
    package_type_id = package_resp.json()["id"]

    list_resp = await client.get(
        "/api/v1/store/package-types",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert any(item["id"] == package_type_id for item in list_resp.json())

    owner_id, pet_id = await _create_owner_and_pet(client, headers, location_id)

    purchase_resp = await client.post(
        "/api/v1/store/packages/purchase",
        json={
            "owner_id": owner_id,
            "package_type_id": package_type_id,
            "quantity": 1,
        },
        headers=headers,
    )
    assert purchase_resp.status_code == 201
    store_invoice_id = purchase_resp.json()["invoice_id"]
    assert store_invoice_id

    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    end_at = start_at + timedelta(days=1)
    reservation_resp = await client.post(
        "/api/v1/reservations",
        json={
            "pet_id": pet_id,
            "location_id": location_id,
            "reservation_type": "boarding",
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "base_rate": "120.00",
        },
        headers=headers,
    )
    assert reservation_resp.status_code == 201
    reservation_id = reservation_resp.json()["id"]

    invoice_resp = await client.post(
        f"/api/v1/reservations/{reservation_id}/invoice",
        headers=headers,
    )
    assert invoice_resp.status_code == 200
    invoice_id = invoice_resp.json()["id"]

    apply_package_resp = await client.post(
        f"/api/v1/store/invoices/{invoice_id}/apply-package-credits",
        headers=headers,
    )
    assert apply_package_resp.status_code == 200
    applied_amount = Decimal(apply_package_resp.json()["applied_amount"])
    assert applied_amount > Decimal("0")

    issue_gc_resp = await client.post(
        "/api/v1/store/gift-certificates/issue",
        json={
            "purchaser_owner_id": owner_id,
            "amount": "50.00",
        },
        headers=headers,
    )
    assert issue_gc_resp.status_code == 201
    gift_code = issue_gc_resp.json()["code"]

    redeem_resp = await client.post(
        "/api/v1/store/gift-certificates/redeem",
        json={"code": gift_code, "owner_id": owner_id},
        headers=headers,
    )
    assert redeem_resp.status_code == 200
    balance = Decimal(redeem_resp.json()["balance"])
    assert balance == Decimal("50.00")

    add_credit_resp = await client.post(
        "/api/v1/store/credit/add",
        json={"owner_id": owner_id, "amount": "25.00", "note": "Adjustment"},
        headers=headers,
    )
    assert add_credit_resp.status_code == 201

    second_start = datetime.now(timezone.utc) + timedelta(days=5)
    second_end = second_start + timedelta(days=1)
    second_reservation = await client.post(
        "/api/v1/reservations",
        json={
            "pet_id": pet_id,
            "location_id": location_id,
            "reservation_type": "boarding",
            "start_at": second_start.isoformat(),
            "end_at": second_end.isoformat(),
            "base_rate": "80.00",
        },
        headers=headers,
    )
    assert second_reservation.status_code == 201
    second_invoice_resp = await client.post(
        f"/api/v1/reservations/{second_reservation.json()['id']}/invoice",
        headers=headers,
    )
    assert second_invoice_resp.status_code == 200
    second_invoice_id = second_invoice_resp.json()["id"]

    apply_credit_resp = await client.post(
        f"/api/v1/store/invoices/{second_invoice_id}/apply-store-credit",
        json={"amount": "40.00"},
        headers=headers,
    )
    assert apply_credit_resp.status_code == 200
    new_balance = Decimal(apply_credit_resp.json()["balance"])
    assert new_balance >= Decimal("0.00")
