"""Integration tests for agreements and icon APIs."""

from __future__ import annotations

from datetime import date
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
    *,
    first_name: str = "Taylor",
) -> tuple[str, str, str]:
    password = "StrongPass1!"
    owner_payload = {
        "first_name": first_name,
        "last_name": "Signer",
        "email": f"{first_name.lower()}.signer@example.com",
        "password": password,
    }
    owner_resp = await client.post(
        "/api/v1/owners", json=owner_payload, headers=headers
    )
    assert owner_resp.status_code == 201
    owner_id = owner_resp.json()["id"]

    pet_payload = {
        "owner_id": owner_id,
        "home_location_id": None,
        "name": f"{first_name}Pet",
        "pet_type": "dog",
        "date_of_birth": date(2020, 1, 1).isoformat(),
    }
    pet_resp = await client.post("/api/v1/pets", json=pet_payload, headers=headers)
    assert pet_resp.status_code == 201
    pet_id = pet_resp.json()["id"]
    return owner_id, pet_id, owner_payload["email"]


async def test_agreement_template_and_signatures(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    manager_token = await _authenticate(client, manager_email, manager_password)
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    owner_id, pet_id, owner_email = await _create_owner_and_pet(
        client, manager_headers, first_name="Casey"
    )

    template_payload = {
        "title": "Boarding Agreement",
        "body": "Please agree to our boarding terms.",
        "requires_signature": True,
        "is_active": True,
        "version": 1,
    }
    template_resp = await client.post(
        "/api/v1/agreements/templates",
        json=template_payload,
        headers=manager_headers,
    )
    assert template_resp.status_code == 201
    template = template_resp.json()

    update_resp = await client.patch(
        f"/api/v1/agreements/templates/{template['id']}",
        json={"version": 2},
        headers=manager_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["version"] == 2

    staff_signature_resp = await client.post(
        "/api/v1/agreements/signatures",
        json={
            "agreement_template_id": template["id"],
            "owner_id": owner_id,
            "pet_id": pet_id,
            "notes": "Signed during check-in",
        },
        headers=manager_headers,
    )
    assert staff_signature_resp.status_code == 201

    owner_token = await _authenticate(client, owner_email, "StrongPass1!")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    owner_signature_resp = await client.post(
        "/api/v1/agreements/signatures",
        json={
            "agreement_template_id": template["id"],
            "pet_id": pet_id,
            "ip_address": "127.0.0.1",
        },
        headers=owner_headers,
    )
    assert owner_signature_resp.status_code == 201

    owner_signatures_resp = await client.get(
        "/api/v1/agreements/signatures",
        headers=owner_headers,
    )
    assert owner_signatures_resp.status_code == 200
    signatures = owner_signatures_resp.json()
    assert any(item["pet_id"] == pet_id for item in signatures)
    assert any(item.get("ip_address") == "127.0.0.1" for item in signatures)


async def test_icon_assignment_and_rendering(app_context: dict[str, Any]) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    owner_id, pet_id, _ = await _create_owner_and_pet(
        client, headers, first_name="Iconic"
    )

    icon_payload = {
        "name": "Peanut Allergy",
        "slug": "peanut-allergy",
        "symbol": "🥜",
        "color": "#ff9900",
        "popup_text": "This pet has a peanut allergy.",
        "affects_capacity": False,
    }
    icon_resp = await client.post("/api/v1/icons", json=icon_payload, headers=headers)
    assert icon_resp.status_code == 201
    icon = icon_resp.json()

    owner_assign_resp = await client.post(
        "/api/v1/icons/owners",
        json={"owner_id": owner_id, "icon_id": icon["id"], "notes": "Allergy"},
        headers=headers,
    )
    assert owner_assign_resp.status_code == 201
    owner_assignment = owner_assign_resp.json()

    pet_assign_resp = await client.post(
        "/api/v1/icons/pets",
        json={"pet_id": pet_id, "icon_id": icon["id"], "notes": "Dietary"},
        headers=headers,
    )
    assert pet_assign_resp.status_code == 201

    icons_list_resp = await client.get("/api/v1/icons", headers=headers)
    assert icons_list_resp.status_code == 200
    assert any(item["slug"] == "peanut-allergy" for item in icons_list_resp.json())

    owner_detail = await client.get(f"/api/v1/owners/{owner_id}", headers=headers)
    assert owner_detail.status_code == 200
    owner_body = owner_detail.json()
    owner_icons = owner_body.get("icons") or owner_body.get("icon_assignments", [])
    assert owner_icons and owner_icons[0]["icon"]["slug"] == "peanut-allergy"

    pet_detail = await client.get(f"/api/v1/pets/{pet_id}", headers=headers)
    assert pet_detail.status_code == 200
    pet_body = pet_detail.json()
    pet_icons = pet_body.get("icons") or pet_body.get("icon_assignments", [])
    assert pet_icons and pet_icons[0]["icon"]["slug"] == "peanut-allergy"

    del_owner_resp = await client.delete(
        f"/api/v1/icons/owners/{owner_assignment['id']}", headers=headers
    )
    assert del_owner_resp.status_code == 204
