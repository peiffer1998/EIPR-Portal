"""Waitlist management services."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.location import Location
from app.models.owner_profile import OwnerProfile
from app.models.pet import Pet
from app.models.waitlist_entry import WaitlistEntry, WaitlistStatus
from app.schemas.waitlist import WaitlistEntryCreate, WaitlistStatusUpdate


async def list_entries(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    status: WaitlistStatus | None = None,
) -> list[WaitlistEntry]:
    stmt: Select[tuple[WaitlistEntry]] = (
        select(WaitlistEntry)
        .where(WaitlistEntry.account_id == account_id)
        .options(selectinload(WaitlistEntry.pet))
        .order_by(WaitlistEntry.created_at.asc())
    )
    if status is not None:
        stmt = stmt.where(WaitlistEntry.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_entry(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> WaitlistEntry | None:
    stmt = (
        select(WaitlistEntry)
        .where(WaitlistEntry.id == entry_id, WaitlistEntry.account_id == account_id)
        .options(selectinload(WaitlistEntry.pet))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_entry(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    payload: WaitlistEntryCreate,
) -> WaitlistEntry:
    location = await session.get(Location, payload.location_id)
    if location is None or location.account_id != account_id:
        raise ValueError("Location not found")

    pet = await session.get(
        Pet,
        payload.pet_id,
        options=[selectinload(Pet.owner).selectinload(OwnerProfile.user)],
    )
    if pet is None or pet.owner.user.account_id != account_id:  # type: ignore[union-attr]
        raise ValueError("Pet not found for account")

    entry = WaitlistEntry(
        account_id=account_id,
        location_id=payload.location_id,
        pet_id=payload.pet_id,
        reservation_type=payload.reservation_type,
        desired_date=payload.desired_date,
        notes=payload.notes,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def update_entry_status(
    session: AsyncSession,
    *,
    entry: WaitlistEntry,
    payload: WaitlistStatusUpdate,
) -> WaitlistEntry:
    new_status = payload.status
    if new_status == entry.status:
        return entry
    entry.status = new_status
    now = datetime.now(UTC)
    if new_status == WaitlistStatus.OFFERED:
        entry.offered_at = now
    elif new_status == WaitlistStatus.CONFIRMED:
        entry.confirmed_at = now
    await session.commit()
    await session.refresh(entry)
    return entry


async def delete_entry(session: AsyncSession, *, entry: WaitlistEntry) -> None:
    await session.delete(entry)
    await session.commit()
