"""API tests for communications endpoints."""

from __future__ import annotations

import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.db.session import get_sessionmaker
from app.models import (
    CampaignSendStatus,
    OwnerProfile,
    ReservationStatus,
    ReservationType,
    PetType,
)
from app.services import pet_service, reservation_service
from app.schemas.comms import CampaignSendRead

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


async def test_comms_flow(app_context: dict[str, object], db_url: str) -> None:
    client: AsyncClient = app_context["client"]  # type: ignore[assignment]
    account_id = UUID(str(app_context["account_id"]))  # type: ignore[index]
    location_id = UUID(str(app_context["location_id"]))  # type: ignore[index]
    manager_email = str(app_context["manager_email"])  # type: ignore[index]
    manager_password = str(app_context["manager_password"])  # type: ignore[index]
    headers = await _auth_manager(
        client,
        email=manager_email,
        password=manager_password,
    )

    # Create an owner with a phone number for SMS flows.
    owner_resp = await client.post(
        "/api/v1/owners",
        json={
            "first_name": "Cora",
            "last_name": "Comms",
            "email": "cora.comms@example.com",
            "password": "Str0ngPass!",
            "phone_number": "+13195550123",
            "sms_opt_in": True,
        },
        headers=headers,
    )
    assert owner_resp.status_code == 201, owner_resp.text
    owner_id = UUID(owner_resp.json()["id"])

    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        owner = await session.get(OwnerProfile, owner_id)
        assert owner is not None
        owner.sms_opt_in = True
        await session.commit()

    # Email template lifecycle.
    create_template = await client.post(
        "/api/v1/comms/emails/templates",
        json={
            "name": "welcome",
            "subject_template": "Welcome {{ owner.first_name }}",
            "html_template": "<p>Hello {{ owner.first_name }}</p>",
        },
        headers=headers,
    )
    assert create_template.status_code == 201, create_template.text
    template_id = UUID(create_template.json()["id"])

    list_templates = await client.get(
        "/api/v1/comms/emails/templates",
        headers=headers,
    )
    assert list_templates.status_code == 200
    assert any(item["id"] == str(template_id) for item in list_templates.json())

    email_send = await client.post(
        "/api/v1/comms/emails/send",
        json={"owner_id": str(owner_id), "template_name": "welcome"},
        headers=headers,
    )
    assert email_send.status_code == 200, email_send.text
    assert email_send.json()["state"] in {"queued", "sent", "failed"}

    # Send SMS to seed conversation.
    sms_send = await client.post(
        "/api/v1/comms/sms/send",
        json={"owner_id": str(owner_id), "body": "Hello from staff"},
        headers=headers,
    )
    assert sms_send.status_code == 201, sms_send.text

    conversations_resp = await client.get(
        "/api/v1/comms/sms/conversations",
        headers=headers,
    )
    assert conversations_resp.status_code == 200
    conversations = conversations_resp.json()
    assert conversations
    conversation_id = conversations[0]["id"]

    messages_resp = await client.get(
        f"/api/v1/comms/sms/conversations/{conversation_id}/messages",
        headers=headers,
    )
    assert messages_resp.status_code == 200
    assert messages_resp.json()

    webhook_resp = await client.post(
        "/api/v1/comms/sms/webhook",
        data={"From": "+13195550123", "Body": "Thanks!"},
    )
    assert webhook_resp.status_code == 202

    # Prepare reservation to use campaign endpoints.
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        pet = await pet_service.create_pet(
            session,
            account_id=account_id,
            owner_id=owner_id,
            home_location_id=location_id,
            name="CommsDog",
            pet_type=PetType.DOG,
            breed=None,
            color=None,
            date_of_birth=None,
            notes=None,
        )
        await session.commit()
        await reservation_service.create_reservation(
            session,
            account_id=account_id,
            pet_id=pet.id,
            location_id=location_id,
            reservation_type=ReservationType.BOARDING,
            start_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
            end_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2),
            base_rate=Decimal("120.00"),
            status=ReservationStatus.CONFIRMED,
        )
        await session.commit()

    preview_resp = await client.post(
        "/api/v1/comms/campaigns/preview",
        json={"channel": "email", "segment": {"has_upcoming_reservation": True}},
        headers=headers,
    )
    assert preview_resp.status_code == 200
    assert preview_resp.json()["count"] == 1

    send_resp = await client.post(
        "/api/v1/comms/campaigns/send-now",
        json={
            "channel": "email",
            "template_name": "welcome",
            "segment": {"has_upcoming_reservation": True},
        },
        headers=headers,
    )
    assert send_resp.status_code == 202, send_resp.text
    sends = [CampaignSendRead.model_validate(item) for item in send_resp.json()]
    assert sends
    assert all(
        send.status in {CampaignSendStatus.SENT, CampaignSendStatus.FAILED}
        for send in sends
    )

    update_template = await client.patch(
        f"/api/v1/comms/emails/templates/{template_id}",
        json={"active": False},
        headers=headers,
    )
    assert update_template.status_code == 200
    assert update_template.json()["active"] is False

    notifications_resp = await client.get(
        "/api/v1/comms/notifications",
        headers=headers,
    )
    assert notifications_resp.status_code == 200
    notifications = notifications_resp.json()["notifications"]
    assert notifications
    notification_id = notifications[0]["id"]

    mark_read_resp = await client.post(
        f"/api/v1/comms/notifications/{notification_id}/read",
        headers=headers,
    )
    assert mark_read_resp.status_code == 200
    assert mark_read_resp.json()["read_at"] is not None

    notifications_after = await client.get(
        "/api/v1/comms/notifications",
        params={"unread_only": "true"},
        headers=headers,
    )
    assert notifications_after.status_code == 200
    assert notifications_after.json()["notifications"] == []
