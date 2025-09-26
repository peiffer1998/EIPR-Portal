"""Waitlist management services."""

from __future__ import annotations

import uuid
from decimal import Decimal
from collections.abc import Iterable
from datetime import UTC, datetime, time, timedelta
from typing import Any, Sequence

from fastapi import BackgroundTasks
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ConfirmationMethod,
    ConfirmationToken,
    Location,
    OwnerProfile,
    Pet,
    Reservation,
    ReservationStatus,
    ReservationType,
    WaitlistEntry,
    WaitlistServiceType,
    WaitlistStatus,
)
from app.schemas.waitlist import (
    WaitlistEntryCreate,
    WaitlistEntryUpdate,
    WaitlistOfferRequest,
    WaitlistOfferResponse,
)
from app.services import audit_service, reservation_service
from app.services.notification_service import (
    schedule_email,
    schedule_sms,
    build_waitlist_offer_email,
    build_waitlist_offer_sms,
)
from app.services import confirmation_service
from app.core.config import get_settings


_SERVICE_TO_RESERVATION = {
    WaitlistServiceType.BOARDING: ReservationType.BOARDING,
    WaitlistServiceType.DAYCARE: ReservationType.DAYCARE,
    WaitlistServiceType.GROOMING: ReservationType.GROOMING,
}


async def add_entry(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: WaitlistEntryCreate,
) -> WaitlistEntry:
    """Create a waitlist entry when capacity is full."""
    location = await session.get(Location, payload.location_id)
    if location is None or location.account_id != account_id:
        raise ValueError("Location not found for account")

    owner = await session.get(
        OwnerProfile,
        payload.owner_id,
        options=[selectinload(OwnerProfile.user)],
    )
    if owner is None or owner.user.account_id != account_id:  # type: ignore[union-attr]
        raise ValueError("Owner not found for account")

    if payload.start_date > payload.end_date:
        raise ValueError("start_date must be on or before end_date")

    if not payload.pets:
        raise ValueError("At least one pet must be provided")

    pet_ids = [pet.pet_id for pet in payload.pets]
    pets = await _fetch_pets(session, pet_ids)
    if set(p.pet_id for p in payload.pets) != {pet.id for pet in pets}:
        raise ValueError("One or more pets could not be found")
    for pet in pets:
        if pet.owner_id != owner.id:
            raise ValueError("Pet does not belong to the owner")

    reservation_type = _SERVICE_TO_RESERVATION[payload.service_type]
    _, minimum = await reservation_service.get_remaining_capacity(
        session,
        account_id=account_id,
        location_id=payload.location_id,
        reservation_type=reservation_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    if minimum is None or minimum > 0:
        raise ValueError("Capacity available; reservation can be booked directly")

    pets_json = [
        {
            "pet_id": str(pet.pet_id),
            "notes": pet.notes,
            "reservation_id": None,
        }
        for pet in payload.pets
    ]
    entry = WaitlistEntry(
        account_id=account_id,
        location_id=payload.location_id,
        owner_id=payload.owner_id,
        service_type=payload.service_type,
        lodging_type_id=payload.lodging_type_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        pets_json=pets_json,
        notes=payload.notes,
        priority=payload.priority or 0,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    await audit_service.record_event(
        session,
        event_type="waitlist.created",
        account_id=account_id,
        user_id=user_id,
        description="Waitlist entry created",
        payload={"waitlist_entry_id": str(entry.id)},
    )
    return entry


async def list_entries(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID | None = None,
    service_type: WaitlistServiceType | None = None,
    status: WaitlistStatus | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> tuple[list[WaitlistEntry], str | None]:
    """Return waitlist entries ordered by priority then FIFO with cursor pagination."""
    stmt = (
        select(WaitlistEntry)
        .where(WaitlistEntry.account_id == account_id)
        .order_by(
            WaitlistEntry.priority.desc(),
            WaitlistEntry.created_at.asc(),
            WaitlistEntry.id.asc(),
        )
        .options(selectinload(WaitlistEntry.location))
    )
    if location_id:
        stmt = stmt.where(WaitlistEntry.location_id == location_id)
    if service_type:
        stmt = stmt.where(WaitlistEntry.service_type == service_type)
    if status:
        stmt = stmt.where(WaitlistEntry.status == status)
    if start_date:
        stmt = stmt.where(WaitlistEntry.start_date >= start_date.date())
    if end_date:
        stmt = stmt.where(WaitlistEntry.start_date <= end_date.date())

    if cursor:
        cursor_entry = await session.get(WaitlistEntry, uuid.UUID(cursor))
        if cursor_entry is None or cursor_entry.account_id != account_id:
            raise ValueError("Invalid cursor")
        stmt = stmt.where(
            or_(
                WaitlistEntry.priority < cursor_entry.priority,
                and_(
                    WaitlistEntry.priority == cursor_entry.priority,
                    WaitlistEntry.created_at > cursor_entry.created_at,
                ),
                and_(
                    WaitlistEntry.priority == cursor_entry.priority,
                    WaitlistEntry.created_at == cursor_entry.created_at,
                    WaitlistEntry.id > cursor_entry.id,
                ),
            )
        )

    result = await session.execute(stmt.limit(min(limit, 100)))
    entries = list(result.scalars().unique().all())
    next_cursor = entries[-1].id.hex if entries else None
    return entries, next_cursor


async def get_entry(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> WaitlistEntry | None:
    stmt = (
        select(WaitlistEntry)
        .where(
            WaitlistEntry.id == entry_id,
            WaitlistEntry.account_id == account_id,
        )
        .options(selectinload(WaitlistEntry.location))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_entry(
    session: AsyncSession,
    *,
    entry: WaitlistEntry,
    payload: WaitlistEntryUpdate,
    user_id: uuid.UUID,
) -> WaitlistEntry:
    updated = False
    if payload.notes is not None and payload.notes != entry.notes:
        entry.notes = payload.notes
        updated = True
    if payload.priority is not None and payload.priority != entry.priority:
        entry.priority = payload.priority
        updated = True
    if payload.status is WaitlistStatus.CANCELED and entry.status not in {
        WaitlistStatus.CANCELED,
        WaitlistStatus.CONVERTED,
    }:
        entry.status = WaitlistStatus.CANCELED
        updated = True
    if not updated:
        return entry
    await session.commit()
    await session.refresh(entry)
    await audit_service.record_event(
        session,
        event_type="waitlist.updated",
        account_id=entry.account_id,
        user_id=user_id,
        description="Waitlist entry updated",
        payload={"waitlist_entry_id": str(entry.id)},
    )
    return entry


async def offer_entry(
    session: AsyncSession,
    *,
    entry: WaitlistEntry,
    user_id: uuid.UUID,
    payload: WaitlistOfferRequest,
    background_tasks: BackgroundTasks,
) -> WaitlistOfferResponse:
    if entry.status is not WaitlistStatus.OPEN:
        raise ValueError("Waitlist entry is not open")

    reservation_type = _SERVICE_TO_RESERVATION[entry.service_type]
    _, minimum = await reservation_service.get_remaining_capacity(
        session,
        account_id=entry.account_id,
        location_id=entry.location_id,
        reservation_type=reservation_type,
        start_date=entry.start_date,
        end_date=entry.end_date,
    )
    if minimum is not None and minimum <= 0:
        raise ValueError("Capacity not yet available")

    reservations = await _create_provisional_reservations(
        session,
        entry=entry,
        lodging_type_id=payload.lodging_type_id,
    )
    now = datetime.now(UTC)
    entry.status = WaitlistStatus.OFFERED
    entry.offered_at = now
    entry.expires_at = now + timedelta(minutes=payload.hold_minutes)
    entry.lodging_type_id = payload.lodging_type_id or entry.lodging_type_id
    entry.converted_reservation_id = reservations[0].id if reservations else None
    entry.pets_json = _attach_reservation_ids(entry.pets_json, reservations)

    token = await confirmation_service.create_token(
        session,
        account_id=entry.account_id,
        reservation_id=reservations[0].id,
        method=payload.method,
        sent_to=payload.sent_to,
        ttl_minutes=payload.hold_minutes,
    )
    await session.commit()
    await session.refresh(entry)

    await audit_service.record_event(
        session,
        event_type="waitlist.offered",
        account_id=entry.account_id,
        user_id=user_id,
        description="Waitlist offer sent",
        payload={"waitlist_entry_id": str(entry.id), "token": token.token},
    )

    _schedule_offer_notification(
        entry=entry,
        token=token,
        ttl_minutes=payload.hold_minutes,
        method=payload.method,
        sent_to=payload.sent_to,
        background_tasks=background_tasks,
    )

    return WaitlistOfferResponse(
        reservation_ids=[reservation.id for reservation in reservations],
        token=token.token,
        expires_at=entry.expires_at,
    )


async def promote_entry(
    session: AsyncSession,
    *,
    entry: WaitlistEntry,
    user_id: uuid.UUID,
    lodging_type_id: uuid.UUID | None = None,
) -> list[Reservation]:
    if entry.status is not WaitlistStatus.OPEN:
        raise ValueError("Waitlist entry is not open")

    reservations = await _create_provisional_reservations(
        session,
        entry=entry,
        lodging_type_id=lodging_type_id,
        status=ReservationStatus.CONFIRMED,
    )
    entry.status = WaitlistStatus.CONVERTED
    entry.offered_at = datetime.now(UTC)
    entry.expires_at = None
    entry.lodging_type_id = lodging_type_id or entry.lodging_type_id
    entry.converted_reservation_id = reservations[0].id if reservations else None
    entry.pets_json = _attach_reservation_ids(entry.pets_json, reservations)
    entry.pets_json = _mark_pets_confirmed(
        entry.pets_json, {res.id for res in reservations}
    )

    await session.commit()
    await session.refresh(entry)

    await audit_service.record_event(
        session,
        event_type="waitlist.promoted",
        account_id=entry.account_id,
        user_id=user_id,
        description="Waitlist entry promoted to confirmed reservation",
        payload={"waitlist_entry_id": str(entry.id)},
    )
    return reservations


async def expire_offers(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    now: datetime | None = None,
) -> int:
    """Expire waitlist offers whose holds have elapsed."""
    now = now or datetime.now(UTC)
    stmt = select(WaitlistEntry).where(
        WaitlistEntry.account_id == account_id,
        WaitlistEntry.status == WaitlistStatus.OFFERED,
        WaitlistEntry.expires_at.is_not(None),
        WaitlistEntry.expires_at < now,
    )
    result = await session.execute(stmt)
    entries = list(result.scalars().unique().all())
    expired_count = 0
    for entry in entries:
        await _cancel_pending_reservations(session, entry=entry)
        entry.status = WaitlistStatus.EXPIRED
        entry.expires_at = None
        expired_count += 1
    if expired_count:
        await session.commit()
    return expired_count


async def confirm_reservation_by_token(
    session: AsyncSession,
    *,
    token_value: str,
) -> tuple[Reservation, WaitlistEntry | None, ConfirmationToken]:
    token = await confirmation_service.get_token(session, token_value)
    if token is None:
        raise ValueError("Invalid confirmation token")
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise ValueError("Confirmation token has expired")

    reservation = await session.get(Reservation, token.reservation_id)
    if reservation is None:
        raise ValueError("Reservation not found for token")

    await confirmation_service.mark_confirmed(session, token)

    reservation = await reservation_service.update_reservation(
        session,
        reservation=reservation,
        account_id=token.account_id,
        status=ReservationStatus.CONFIRMED,
    )

    entry = await _find_entry_by_reservation(session, token.account_id, reservation.id)
    if entry:
        reservation_ids = {
            uuid.UUID(item["reservation_id"])
            for item in entry.pets_json
            if item.get("reservation_id")
        }
        updated_ids: set[uuid.UUID] = set()
        for res_id in reservation_ids:
            existing = await session.get(Reservation, res_id)
            if existing is None:
                continue
            if existing.status != ReservationStatus.CONFIRMED:
                existing = await reservation_service.update_reservation(
                    session,
                    reservation=existing,
                    account_id=token.account_id,
                    status=ReservationStatus.CONFIRMED,
                )
            updated_ids.add(existing.id)
        entry.status = WaitlistStatus.CONVERTED
        entry.expires_at = None
        entry.converted_reservation_id = reservation.id
        entry.pets_json = _mark_pets_confirmed(entry.pets_json, reservation_ids)
        await session.commit()
        await session.refresh(entry)

    await audit_service.record_event(
        session,
        event_type="waitlist.confirmed",
        account_id=token.account_id,
        user_id=None,
        description="Waitlist offer confirmed",
        payload={"waitlist_entry_id": str(entry.id) if entry else None},
    )

    return reservation, entry, token


async def _fetch_pets(
    session: AsyncSession, pet_ids: Iterable[uuid.UUID]
) -> Sequence[Pet]:
    result = await session.execute(select(Pet).where(Pet.id.in_(list(pet_ids))))
    return result.scalars().all()


async def _create_provisional_reservations(
    session: AsyncSession,
    *,
    entry: WaitlistEntry,
    lodging_type_id: uuid.UUID | None,
    status: ReservationStatus = ReservationStatus.PENDING_CONFIRMATION,
) -> list[Reservation]:
    reservations: list[Reservation] = []
    start_at = datetime.combine(entry.start_date, time.min, tzinfo=UTC)
    end_at = datetime.combine(entry.end_date + timedelta(days=1), time.min, tzinfo=UTC)
    reservation_type = _SERVICE_TO_RESERVATION[entry.service_type]
    for pet_payload in entry.pets_json:
        pet_id = uuid.UUID(str(pet_payload["pet_id"]))
        reservation = await reservation_service.create_reservation(
            session,
            account_id=entry.account_id,
            pet_id=pet_id,
            location_id=entry.location_id,
            reservation_type=reservation_type,
            start_at=start_at,
            end_at=end_at,
            base_rate=Decimal("0"),
            status=status,
            notes=entry.notes,
            kennel_id=lodging_type_id,
        )
        reservations.append(reservation)
    return reservations


async def _cancel_pending_reservations(
    session: AsyncSession, *, entry: WaitlistEntry
) -> None:
    reservation_ids = [
        uuid.UUID(res_id)
        for res_id in (
            item.get("reservation_id")
            for item in entry.pets_json
            if item.get("reservation_id")
        )
    ]
    for reservation_id in reservation_ids:
        reservation = await session.get(Reservation, reservation_id)
        if reservation and reservation.status in {
            ReservationStatus.PENDING_CONFIRMATION,
            ReservationStatus.OFFERED_FROM_WAITLIST,
        }:
            await reservation_service.update_reservation(
                session,
                reservation=reservation,
                account_id=entry.account_id,
                status=ReservationStatus.CANCELED,
            )


def _attach_reservation_ids(
    pets_json: list[dict[str, Any]], reservations: list[Reservation]
) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    for payload, reservation in zip(pets_json, reservations, strict=False):
        payload = dict(payload)
        payload["reservation_id"] = str(reservation.id)
        updated.append(payload)
    updated.extend(pets_json[len(updated) :])
    return updated


def _mark_pets_confirmed(
    pets_json: list[dict[str, Any]], reservation_ids: set[uuid.UUID]
) -> list[dict[str, Any]]:
    timestamp = datetime.now(UTC).isoformat()
    string_ids = {str(res_id) for res_id in reservation_ids}
    updated: list[dict[str, Any]] = []
    for payload in pets_json:
        payload = dict(payload)
        if payload.get("reservation_id") in string_ids:
            payload["confirmed_at"] = timestamp
        updated.append(payload)
    return updated


async def _find_entry_by_reservation(
    session: AsyncSession,
    account_id: uuid.UUID,
    reservation_id: uuid.UUID,
) -> WaitlistEntry | None:
    stmt = select(WaitlistEntry).where(WaitlistEntry.account_id == account_id)
    result = await session.execute(stmt)
    for entry in result.scalars().unique():
        for pet in entry.pets_json:
            if pet.get("reservation_id") == str(reservation_id):
                return entry
    return None


def _schedule_offer_notification(
    *,
    entry: WaitlistEntry,
    token: ConfirmationToken,
    ttl_minutes: int,
    method: str,
    sent_to: str | None,
    background_tasks: BackgroundTasks,
) -> None:
    settings = get_settings()
    confirm_url = f"/api/v1/reservations/confirm/{token.token}"
    start = entry.start_date.isoformat()
    end = entry.end_date.isoformat()
    location_name = entry.location.name if entry.location else "Eastern Iowa Pet Resort"
    if method == ConfirmationMethod.EMAIL.value:
        if not sent_to or not settings.smtp_host:
            return
        subject, body = build_waitlist_offer_email(
            start_date=start,
            end_date=end,
            location_name=location_name,
            ttl_minutes=ttl_minutes,
            confirm_url=confirm_url,
        )
        schedule_email(
            background_tasks, recipients=[sent_to], subject=subject, body=body
        )
    elif method == ConfirmationMethod.SMS.value:
        if not sent_to:
            return
        message = build_waitlist_offer_sms(
            start_date=start,
            end_date=end,
            ttl_minutes=ttl_minutes,
            confirm_url=confirm_url,
        )
        schedule_sms(background_tasks, phone_numbers=[sent_to], message=message)
