"""Integration tests for owner and pet APIs."""

from __future__ import annotations

from typing import Any
import uuid

import pytest
from httpx import AsyncClient

from app.db.session import get_sessionmaker
from app.models import Account, OwnerProfile, User, UserRole, UserStatus
from app.core.security import get_password_hash
from app.services import note_buffer

pytestmark = pytest.mark.asyncio


async def _authenticate(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    payload = response.json()
    return payload["access_token"]


async def test_owner_pet_lifecycle(app_context: dict[str, Any]) -> None:
    note_buffer.clear_all()
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]
    location_id = str(app_context["location_id"])

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    owner_payload = {
        "first_name": "Alex",
        "last_name": "PetParent",
        "email": "alex.parent@example.com",
        "password": "SecurePass1!",
        "phone_number": "555-0100",
        "preferred_contact_method": "email",
        "notes": "Loves daily updates",
        "is_primary_contact": True,
    }
    create_owner_resp = await client.post(
        "/api/v1/owners", json=owner_payload, headers=headers
    )
    assert create_owner_resp.status_code == 201
    owner_id = create_owner_resp.json()["id"]

    list_resp = await client.get("/api/v1/owners", headers=headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == owner_id for item in list_resp.json())

    search_resp = await client.get(
        "/api/v1/owners",
        params={"q": "Alex"},
        headers=headers,
    )
    assert search_resp.status_code == 200
    assert any(item["id"] == owner_id for item in search_resp.json())

    pet_payload = {
        "owner_id": owner_id,
        "home_location_id": location_id,
        "name": "Bailey",
        "pet_type": "dog",
        "breed": "Labradoodle",
        "color": "Apricot",
        "date_of_birth": "2020-05-01",
        "notes": "Requires hypoallergenic shampoo",
    }
    create_pet_resp = await client.post(
        "/api/v1/pets", json=pet_payload, headers=headers
    )
    assert create_pet_resp.status_code == 201
    pet_body = create_pet_resp.json()
    assert pet_body["owner_id"] == owner_id
    assert pet_body["name"] == "Bailey"
    assert pet_body["owner"]["id"] == owner_id
    assert pet_body["owner"]["email"] == owner_payload["email"]

    pets_list = await client.get("/api/v1/pets", headers=headers)
    assert pets_list.status_code == 200
    pets_payload = pets_list.json()
    assert any(item["id"] == pet_body["id"] for item in pets_payload)
    assert any(
        item.get("owner", {}).get("email") == owner_payload["email"]
        for item in pets_payload
    )

    owner_filtered = await client.get(
        f"/api/v1/pets?owner_id={owner_id}", headers=headers
    )
    assert owner_filtered.status_code == 200
    filtered_payload = owner_filtered.json()
    assert len(filtered_payload) >= 1
    assert all(item["owner_id"] == owner_id for item in filtered_payload)

    search_resp = await client.get("/api/v1/pets?q=Bailey", headers=headers)
    assert search_resp.status_code == 200
    assert any(item["id"] == pet_body["id"] for item in search_resp.json())

    # Notes API placeholders
    add_note_resp = await client.post(
        f"/api/v1/pets/{pet_body['id']}/notes",
        json={"text": "Great temperament"},
        headers=headers,
    )
    assert add_note_resp.status_code == 201
    notes_resp = await client.get(
        f"/api/v1/pets/{pet_body['id']}/notes", headers=headers
    )
    assert notes_resp.status_code == 200
    assert any(note["text"] == "Great temperament" for note in notes_resp.json())

    # Vaccination alias should respond
    vacc_resp = await client.get(
        f"/api/v1/pets/{pet_body['id']}/vaccinations", headers=headers
    )
    assert vacc_resp.status_code == 200


async def test_owner_access_is_account_scoped(
    app_context: dict[str, Any], db_url: str
) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    manager_email = app_context["manager_email"]
    manager_password = app_context["manager_password"]

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    owner_payload = {
        "first_name": "Jamie",
        "last_name": "Owner",
        "email": "jamie.owner@example.com",
        "password": "SecurePass1!",
    }
    create_owner_resp = await client.post(
        "/api/v1/owners", json=owner_payload, headers=headers
    )
    assert create_owner_resp.status_code == 201
    owner_id = create_owner_resp.json()["id"]

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        other_account = Account(
            name="Other Resort", slug=f"other-{uuid.uuid4().hex[:6]}"
        )
        session.add(other_account)
        await session.flush()

        other_manager = User(
            account_id=other_account.id,
            email="other.manager@example.com",
            hashed_password=get_password_hash("DiffPass1!"),
            first_name="Owen",
            last_name="Manager",
            role=UserRole.MANAGER,
            status=UserStatus.ACTIVE,
        )
        session.add(other_manager)

        stray_owner = OwnerProfile(
            user=User(
                account_id=other_account.id,
                email="stray.owner@example.com",
                hashed_password=get_password_hash("AnotherPass1!"),
                first_name="Stray",
                last_name="Owner",
                role=UserRole.PET_PARENT,
                status=UserStatus.ACTIVE,
            )
        )
        session.add(stray_owner)
        await session.commit()

    other_token = await _authenticate(client, "other.manager@example.com", "DiffPass1!")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Attempt to fetch owner from another account should return 404
    response = await client.get(f"/api/v1/owners/{owner_id}", headers=other_headers)
    assert response.status_code == 404
