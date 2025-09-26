"""Integration tests for extended services (catalog, packages, waitlists, documents)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
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


async def _create_owner_and_pet(
    client: AsyncClient,
    headers: dict[str, str],
    location_id: str,
) -> tuple[str, str]:
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Jordan",
            "last_name": "Client",
            "email": "jordan.client@example.com",
            "password": "OwnerPass1!",
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
            "name": "Mochi",
            "pet_type": "dog",
        },
        headers=headers,
    )
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]
    return owner_id, pet_id


async def test_service_catalog_and_packages(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    # Create service catalog item (service)
    create_resp = await client.post(
        "/api/v1/service-items",
        json={
            "name": "Full Groom",
            "description": "Spa day for pups",
            "kind": "service",
            "reservation_type": "grooming",
            "duration_minutes": 120,
            "base_price": "85.00",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    # Update item to mark inactive
    update_resp = await client.patch(
        f"/api/v1/service-items/{item_id}",
        json={"active": False},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["active"] is False

    # Create retail catalog item (no reservation type)
    retail_resp = await client.post(
        "/api/v1/service-items",
        json={
            "name": "Dog Treat Pack",
            "kind": "retail",
            "base_price": "12.50",
            "sku": "TREAT-001",
        },
        headers=headers,
    )
    assert retail_resp.status_code == 201

    list_resp = await client.get("/api/v1/service-items", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    # Create package
    package_resp = await client.post(
        "/api/v1/packages",
        json={
            "name": "10-Day Daycare",
            "reservation_type": "daycare",
            "credit_quantity": 10,
            "price": "320.00",
        },
        headers=headers,
    )
    assert package_resp.status_code == 201
    package_id = package_resp.json()["id"]

    # Update package price
    package_update = await client.patch(
        f"/api/v1/packages/{package_id}",
        json={"price": "300.00"},
        headers=headers,
    )
    assert package_update.status_code == 200
    assert package_update.json()["price"] == "300.00"


async def test_waitlist_location_hours_and_documents(
    app_context: dict[str, Any],
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    owner_id, pet_id = await _create_owner_and_pet(client, headers, location_id)

    start_dt = datetime.combine(date.today(), time.min, tzinfo=UTC)
    end_dt = start_dt + timedelta(days=1)
    blocker_resp = await client.post(
        "/api/v1/reservations",
        json={
            "pet_id": pet_id,
            "location_id": location_id,
            "reservation_type": "boarding",
            "start_at": start_dt.isoformat(),
            "end_at": end_dt.isoformat(),
            "base_rate": "75.00",
            "status": "confirmed",
        },
        headers=headers,
    )
    assert blocker_resp.status_code == 201

    # Create waitlist entry
    waitlist_resp = await client.post(
        "/api/v1/waitlist",
        json={
            "location_id": location_id,
            "owner_id": owner_id,
            "service_type": "boarding",
            "start_date": date.today().isoformat(),
            "end_date": date.today().isoformat(),
            "pets": [{"pet_id": pet_id}],
            "notes": "Needs large kennel",
        },
        headers=headers,
    )
    assert waitlist_resp.status_code == 201
    entry_id = waitlist_resp.json()["id"]

    waitlist_list = await client.get(
        "/api/v1/waitlist",
        params={"limit": 5},
        headers=headers,
    )
    assert waitlist_list.status_code == 200
    assert any(entry["id"] == entry_id for entry in waitlist_list.json()["entries"])

    # Set location hours
    hour_resp = await client.put(
        f"/api/v1/locations/{location_id}/hours",
        json={
            "day_of_week": 0,
            "open_time": "07:00:00",
            "close_time": "19:00:00",
        },
        headers=headers,
    )
    assert hour_resp.status_code == 200
    hour_id = hour_resp.json()["id"]

    # Update hour to closed
    hour_update = await client.patch(
        f"/api/v1/locations/{location_id}/hours/{hour_id}",
        json={"is_closed": True},
        headers=headers,
    )
    assert hour_update.status_code == 200
    assert hour_update.json()["is_closed"] is True

    # Create closure
    closure_resp = await client.post(
        f"/api/v1/locations/{location_id}/closures",
        json={
            "start_date": date.today().isoformat(),
            "end_date": date.today().isoformat(),
            "reason": "Holiday",
        },
        headers=headers,
    )
    assert closure_resp.status_code == 201
    closure_id = closure_resp.json()["id"]

    # Document upload metadata
    doc_resp = await client.post(
        "/api/v1/documents",
        json={
            "file_name": "vaccination.pdf",
            "content_type": "application/pdf",
            "url": "https://files.example.com/vaccination.pdf",
            "owner_id": owner_id,
            "pet_id": pet_id,
            "notes": "Rabies certificate",
        },
        headers=headers,
    )
    assert doc_resp.status_code == 201
    document_id = doc_resp.json()["id"]

    docs_list = await client.get(
        "/api/v1/documents",
        params={"pet_id": pet_id},
        headers=headers,
    )
    assert docs_list.status_code == 200
    assert any(doc["id"] == document_id for doc in docs_list.json())

    # Cleanup
    delete_doc = await client.delete(
        f"/api/v1/documents/{document_id}", headers=headers
    )
    assert delete_doc.status_code == 204

    delete_closure = await client.delete(
        f"/api/v1/locations/{location_id}/closures/{closure_id}",
        headers=headers,
    )
    assert delete_closure.status_code == 204

    cancel_waitlist = await client.patch(
        f"/api/v1/waitlist/{entry_id}",
        json={"status": "canceled"},
        headers=headers,
    )
    assert cancel_waitlist.status_code == 200
