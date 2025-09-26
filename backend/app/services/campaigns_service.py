"""Audience segmentation and campaign sends for email/SMS."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Campaign,
    CampaignChannel,
    CampaignSend,
    CampaignSendStatus,
    CampaignState,
    EmailTemplate,
    OwnerProfile,
    Reservation,
    ReservationStatus,
    User,
    UserStatus,
    Pet,
)
from app.services import sms_service
from app.services.email_service import render_template, send_template  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

_ACTIVE_RESERVATION_STATUSES = {
    ReservationStatus.REQUESTED,
    ReservationStatus.ACCEPTED,
    ReservationStatus.CONFIRMED,
    ReservationStatus.CHECKED_IN,
}


def _segment_filter(segment: dict[str, Any] | None) -> dict[str, Any]:
    return segment or {}


def _upcoming_reservations_clause(
    segment: dict[str, Any], owner_id_field
) -> Select[bool]:
    now = datetime.now(UTC)
    stmt = (
        select(Reservation.id)
        .join(Pet, Pet.id == Reservation.pet_id)
        .where(
            Pet.owner_id == owner_id_field,
            Reservation.start_at >= now,
            Reservation.status.in_(_ACTIVE_RESERVATION_STATUSES),
        )
    )
    location_id = segment.get("location_id")
    if location_id:
        stmt = stmt.where(Reservation.location_id == UUID(str(location_id)))
    return stmt.exists()


async def preview(
    session: AsyncSession,
    *,
    account_id: UUID,
    segment: dict[str, Any] | None,
) -> int:
    filters = _segment_filter(segment)
    stmt = (
        select(func.count(OwnerProfile.id))
        .join(OwnerProfile.user)
        .where(
            OwnerProfile.user.has(User.account_id == account_id),
            OwnerProfile.user.has(User.status == UserStatus.ACTIVE),
        )
    )
    if filters.get("has_upcoming_reservation"):
        stmt = stmt.where(_upcoming_reservations_clause(filters, OwnerProfile.id))
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def _recipient_ids(
    session: AsyncSession,
    account_id: UUID,
    filters: dict[str, Any],
) -> list[UUID]:
    stmt = (
        select(OwnerProfile.id)
        .join(OwnerProfile.user)
        .where(
            OwnerProfile.user.has(User.account_id == account_id),
            OwnerProfile.user.has(User.status == UserStatus.ACTIVE),
        )
    )
    if filters.get("has_upcoming_reservation"):
        stmt = stmt.where(_upcoming_reservations_clause(filters, OwnerProfile.id))
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def _first_upcoming_reservation(
    session: AsyncSession, owner_id: UUID
) -> Reservation | None:
    now = datetime.now(UTC)
    stmt = (
        select(Reservation)
        .join(Pet, Pet.id == Reservation.pet_id)
        .options(selectinload(Reservation.pet))
        .where(
            Pet.owner_id == owner_id,
            Reservation.start_at >= now,
            Reservation.status.in_(_ACTIVE_RESERVATION_STATUSES),
        )
        .order_by(Reservation.start_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def send_now(
    session: AsyncSession,
    *,
    account_id: UUID,
    channel: CampaignChannel,
    template_name: str,
    segment: dict[str, Any] | None,
) -> UUID:
    filters = _segment_filter(segment)
    recipient_ids = await _recipient_ids(session, account_id, filters)

    campaign = Campaign(
        account_id=account_id,
        channel=channel,
        name=f"Campaign {datetime.now(UTC).isoformat()}",
        template_id=None,
        segment=filters,
        state=CampaignState.SENDING,
        created_at=datetime.now(UTC),
    )
    session.add(campaign)
    await session.flush()

    template_stmt = select(EmailTemplate).where(
        EmailTemplate.account_id == account_id,
        EmailTemplate.name == template_name,
        EmailTemplate.active.is_(True),
    )
    template = (await session.execute(template_stmt)).scalar_one_or_none()
    if template is None:
        raise ValueError("Template not found for campaign")
    campaign.template_id = template.id

    send_records: list[CampaignSend] = []
    for owner_id in recipient_ids:
        reservation = await _first_upcoming_reservation(session, owner_id)
        context: dict[str, Any] = {}
        if reservation is not None:
            context["reservation"] = {"start": reservation.start_at.isoformat()}
            if reservation.pet is not None:
                context["pet"] = {"name": reservation.pet.name}

        send = CampaignSend(
            account_id=account_id,
            campaign_id=campaign.id,
            owner_id=owner_id,
            channel=channel,
            status=CampaignSendStatus.QUEUED,
        )
        session.add(send)
        await session.flush()

        try:
            if channel is CampaignChannel.EMAIL:
                await send_template(
                    session,
                    owner_id=owner_id,
                    template_name=template_name,
                    context=context,
                )
                send.status = CampaignSendStatus.SENT
                send.sent_at = datetime.now(UTC)
            else:
                _subject, body = render_template(template, context)
                await sms_service.send_sms(session, owner_id=owner_id, body=body)
                send.status = CampaignSendStatus.SENT
                send.sent_at = datetime.now(UTC)
        except Exception as exc:  # pragma: no cover - external services
            logger.exception("Campaign send failure for owner %s: %s", owner_id, exc)
            send.status = CampaignSendStatus.FAILED
            send.error = str(exc)
        send_records.append(send)

    campaign.state = (
        CampaignState.DONE
        if all(record.status is CampaignSendStatus.SENT for record in send_records)
        else CampaignState.FAILED
    )
    await session.commit()
    return campaign.id
