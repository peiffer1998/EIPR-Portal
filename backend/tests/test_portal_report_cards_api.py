"""Owner portal report card API tests."""

from __future__ import annotations

import os
import uuid
from datetime import date
from typing import Any

import pytest

from app.api import deps
from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.models import OwnerProfile, Pet, PetType, User, UserRole, UserStatus
from app.services import report_card_service

pytestmark = pytest.mark.asyncio


async def _portal_auth(client, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/portal/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def test_owner_can_view_report_cards(
    app_context: dict[str, Any], db_url: str
) -> None:
    client = app_context["client"]
    account_id: uuid.UUID = app_context["account_id"]
    account_slug: str = app_context["account_slug"]
    manager_email: str = app_context["manager_email"]

    os.environ["PORTAL_ACCOUNT_SLUG"] = account_slug
    get_settings.cache_clear()
    get_settings()
    deps._build_s3_client.cache_clear()

    owner_email = f"parent+{uuid.uuid4().hex[:5]}@example.com"
    owner_password = "OwnerPortal1!"

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        manager_row = await session.execute(
            User.__table__.select().where(User.email == manager_email)
        )
        manager_result = manager_row.first()
        assert manager_result is not None
        manager_id = manager_result[0]

        owner_user = User(
            account_id=account_id,
            email=owner_email,
            hashed_password=get_password_hash(owner_password),
            first_name="Jordan",
            last_name="Parent",
            role=UserRole.PET_PARENT,
            status=UserStatus.ACTIVE,
        )
        session.add(owner_user)
        await session.flush()

        owner = OwnerProfile(user_id=owner_user.id)
        session.add(owner)
        await session.flush()

        pet = Pet(owner_id=owner.id, name="Luna", pet_type=PetType.DOG)
        session.add(pet)
        await session.flush()

        await report_card_service.create_card(
            session,
            account_id=account_id,
            owner_id=owner.id,
            pet_id=pet.id,
            created_by_user_id=manager_id,
            occurred_on=date(2025, 1, 5),
            title="Daily Update",
            summary="Luna enjoyed the splash pad!",
            rating=4,
        )

    token = await _portal_auth(client, owner_email, owner_password)
    headers = {"Authorization": f"Bearer {token}"}

    list_resp = await client.get("/api/v1/portal/report-cards", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    cards = list_resp.json()
    assert len(cards) == 1
    card_id = cards[0]["id"]
    assert cards[0]["pet_name"] == "Luna"

    detail_resp = await client.get(
        f"/api/v1/portal/report-cards/{card_id}", headers=headers
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["summary"] == "Luna enjoyed the splash pad!"
    assert detail["owner_id"] == cards[0]["owner_id"]
