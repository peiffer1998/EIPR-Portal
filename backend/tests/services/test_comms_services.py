"""Service-level tests for communications (email, SMS, campaigns, notifications)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_sessionmaker
from app.models import (
    Account,
    CampaignChannel,
    CampaignSend,
    CampaignSendStatus,
    EmailOutbox,
    EmailTemplate,
    Location,
    NotificationType,
    OwnerProfile,
    Pet,
    PetType,
    Reservation,
    ReservationStatus,
    ReservationType,
    SMSMessage,
    User,
    UserRole,
    UserStatus,
)
from app.services import campaigns_service, notifications_service, sms_service
from app.services.email_service import render_template, send_template  # type: ignore[attr-defined]

pytestmark = pytest.mark.asyncio


async def _seed_owner(session, *, sms_opt_in: bool = True) -> tuple[UUID, UUID, UUID]:
    account = Account(name="Comms Resort", slug=f"comms-{uuid4().hex[:6]}")
    session.add(account)
    await session.flush()

    user = User(
        account_id=account.id,
        email="owner@example.com",
        hashed_password="x",
        first_name="Taylor",
        last_name="Test",
        phone_number="3195550101",
        role=UserRole.PET_PARENT,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    await session.flush()

    owner = OwnerProfile(user_id=user.id, sms_opt_in=sms_opt_in)
    session.add(owner)
    await session.flush()
    return owner.id, account.id, user.id


async def test_email_render_and_send(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        owner_id, account_id, _ = await _seed_owner(session)
        template = EmailTemplate(
            account_id=account_id,
            name="welcome",
            subject_template="Welcome {{ owner.first_name }}",
            html_template="<p>Hello {{ owner.first_name }} and {{ pet.name }}</p>",
        )
        session.add(template)
        await session.commit()
        template_id = template.id

    async with sessionmaker() as session:
        owner = (
            await session.execute(
                select(OwnerProfile)
                .options(selectinload(OwnerProfile.user))
                .where(OwnerProfile.id == owner_id)
            )
        ).scalar_one()
        template = await session.get(EmailTemplate, template_id)
        assert template is not None

        subject, html = render_template(
            template,
            {"owner": {"first_name": owner.user.first_name}, "pet": {"name": "Buddy"}},
        )
        assert "Welcome" in subject
        assert "Buddy" in html

        outbox_id = await send_template(
            session,
            owner_id=owner.id,
            template_name="welcome",
            context={"pet": {"name": "Buddy"}},
        )
        outbox = await session.get(EmailOutbox, outbox_id)
        assert outbox is not None
        assert outbox.state.value in {"sent", "queued", "failed"}


async def test_sms_send_and_inbound(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        owner_id, account_id, _ = await _seed_owner(session)
        await session.commit()

    async with sessionmaker() as session:
        message_id = await sms_service.send_sms(
            session, owner_id=owner_id, body="Test message"
        )
        message = await session.get(SMSMessage, message_id)
        assert message is not None
        assert message.status.value in {"sent", "queued"}

        inbound_id = await sms_service.record_inbound(
            session,
            account_id=account_id,
            owner_id=owner_id,
            phone_e164="+13195550101",
            body="Hello",
            provider_message_id="inbound-1",
        )
        inbound = await session.get(SMSMessage, inbound_id)
        assert inbound is not None
        assert inbound.direction.value == "in"
        assert inbound.status.value == "received"


async def test_campaign_preview_and_send(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        owner_id, account_id, _ = await _seed_owner(session)
        location = Location(account_id=account_id, name="Main", timezone="UTC")
        session.add(location)
        await session.flush()

        pet = Pet(owner_id=owner_id, name="Scout", pet_type=PetType.DOG)
        session.add(pet)
        await session.flush()

        reservation = Reservation(
            account_id=account_id,
            location_id=location.id,
            pet_id=pet.id,
            reservation_type=ReservationType.BOARDING,
            status=ReservationStatus.CONFIRMED,
            start_at=datetime.now(timezone.utc) + timedelta(days=1),
            end_at=datetime.now(timezone.utc) + timedelta(days=2),
            base_rate=100,
        )
        session.add(reservation)

        template = EmailTemplate(
            account_id=account_id,
            name="reminder",
            subject_template="Upcoming stay",
            html_template="<p>See you soon {{ owner.first_name }}</p>",
        )
        session.add(template)
        await session.commit()

    async with sessionmaker() as session:
        count = await campaigns_service.preview(
            session,
            account_id=account_id,
            segment={"has_upcoming_reservation": True},
        )
        assert count == 1

        campaign_id = await campaigns_service.send_now(
            session,
            account_id=account_id,
            channel=CampaignChannel.EMAIL,
            template_name="reminder",
            segment={"has_upcoming_reservation": True},
        )
        await session.commit()
        sends = (
            (
                await session.execute(
                    select(CampaignSend).where(CampaignSend.campaign_id == campaign_id)
                )
            )
            .scalars()
            .all()
        )
        assert sends
        assert all(
            s.status in {CampaignSendStatus.SENT, CampaignSendStatus.FAILED}
            for s in sends
        )


async def test_notifications(reset_database, db_url: str) -> None:
    sessionmaker = get_sessionmaker(db_url)
    async with sessionmaker() as session:
        owner_id, account_id, user_id = await _seed_owner(session)
        await notifications_service.notify(
            session,
            account_id=account_id,
            user_id=user_id,
            type=NotificationType.SYSTEM,
            title="Test",
            body="Body",
        )

        unread = await notifications_service.list_for_user(
            session,
            account_id=account_id,
            user_id=user_id,
            unread_only=True,
        )
        assert len(unread) == 1

        notification_id = unread[0].id
        await notifications_service.mark_read(
            session,
            notification_id=notification_id,
            user_id=user_id,
        )

        all_items = await notifications_service.list_for_user(
            session,
            account_id=account_id,
            user_id=user_id,
        )
        assert len(all_items) == 1
        assert all_items[0].read_at is not None
