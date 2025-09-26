"""Integration tests for the report card staff API."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import (
    Document,
    OwnerProfile,
    Pet,
    PetType,
    User,
    UserRole,
    UserStatus,
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


async def _seed_owner_pet_and_documents(
    db_url: str,
    *,
    account_id: uuid.UUID,
    manager_email: str,
) -> dict[str, Any]:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        manager_query = await session.execute(
            User.__table__.select().where(User.email == manager_email)
        )
        manager_row = manager_query.first()
        assert manager_row is not None, "Manager must exist"
        manager_id = manager_row[0]

        owner_user = User(
            account_id=account_id,
            email=f"owner+{uuid.uuid4().hex[:6]}@example.com",
            hashed_password=get_password_hash("Owner123!"),
            first_name="Taylor",
            last_name="Guardian",
            role=UserRole.PET_PARENT,
            status=UserStatus.ACTIVE,
        )
        session.add(owner_user)
        await session.flush()

        owner = OwnerProfile(user_id=owner_user.id)
        session.add(owner)
        await session.flush()

        pet = Pet(owner_id=owner.id, name="Rex", pet_type=PetType.DOG)
        session.add(pet)
        await session.flush()

        friend = Pet(owner_id=owner.id, name="Milo", pet_type=PetType.DOG)
        session.add(friend)
        await session.flush()

        doc1 = Document(
            account_id=account_id,
            owner_id=owner.id,
            pet_id=pet.id,
            uploaded_by_user_id=manager_id,
            file_name="playtime.jpg",
            content_type="image/jpeg",
            object_key="documents/playtime.jpg",
            url="https://cdn.example.com/playtime.jpg",
        )
        session.add(doc1)
        await session.flush()

        doc2 = Document(
            account_id=account_id,
            owner_id=owner.id,
            pet_id=pet.id,
            uploaded_by_user_id=manager_id,
            file_name="naptime.jpg",
            content_type="image/jpeg",
            object_key="documents/naptime.jpg",
            url="https://cdn.example.com/naptime.jpg",
        )
        session.add(doc2)
        await session.commit()

        return {
            "owner_id": owner.id,
            "pet_id": pet.id,
            "friend_pet_id": friend.id,
            "document_ids": [doc1.id, doc2.id],
        }


async def test_report_card_staff_flow(app_context: dict[str, Any], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_id: uuid.UUID = app_context["account_id"]
    manager_email: str = app_context["manager_email"]
    manager_password: str = app_context["manager_password"]
    seed = await _seed_owner_pet_and_documents(
        db_url,
        account_id=account_id,
        manager_email=manager_email,
    )

    token = await _authenticate(client, manager_email, manager_password)
    headers = {"Authorization": f"Bearer {token}"}

    occurred_on = date.today().isoformat()
    create_resp = await client.post(
        "/api/v1/report-cards",
        headers=headers,
        json={
            "owner_id": str(seed["owner_id"]),
            "pet_id": str(seed["pet_id"]),
            "occurred_on": occurred_on,
            "title": "Daily Report",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    card = create_resp.json()
    card_id = card["id"]
    assert card["status"] == "draft"

    patch_resp = await client.patch(
        f"/api/v1/report-cards/{card_id}",
        headers=headers,
        json={"summary": "Rex had a great day", "rating": 5},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    assert patch_resp.json()["summary"] == "Rex had a great day"

    media_resp = await client.post(
        f"/api/v1/report-cards/{card_id}/media",
        headers=headers,
        json={"document_ids": [str(d) for d in seed["document_ids"]]},
    )
    assert media_resp.status_code == 200, media_resp.text
    media_body = media_resp.json()
    assert len(media_body["media"]) == 2
    assert media_body["media"][0]["document"]["file_name"] == "playtime.jpg"

    friends_resp = await client.post(
        f"/api/v1/report-cards/{card_id}/friends",
        headers=headers,
        json={"friend_pet_ids": [str(seed["friend_pet_id"])]},
    )
    assert friends_resp.status_code == 200, friends_resp.text
    assert len(friends_resp.json()["friends"]) == 1

    send_resp = await client.post(
        f"/api/v1/report-cards/{card_id}/send", headers=headers
    )
    assert send_resp.status_code == 200, send_resp.text
    assert send_resp.json()["status"] == "sent"

    get_resp = await client.get(f"/api/v1/report-cards/{card_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["pet_name"] == "Rex"

    list_resp = await client.get(
        "/api/v1/report-cards",
        headers=headers,
        params={"pet_id": str(seed["pet_id"]), "date_from": occurred_on},
    )
    assert list_resp.status_code == 200
    cards = list_resp.json()
    assert len(cards) == 1
    assert cards[0]["id"] == card_id
