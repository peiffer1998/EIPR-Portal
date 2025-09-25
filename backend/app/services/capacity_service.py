"""Location capacity management services."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.location_capacity import LocationCapacityRule
from app.models.reservation import ReservationType


async def list_capacity_rules(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
) -> list[LocationCapacityRule]:
    """Return all capacity rules for a location scoped to an account."""
    await _ensure_location_access(session, account_id=account_id, location_id=location_id)
    result = await session.execute(
        select(LocationCapacityRule)
        .where(LocationCapacityRule.location_id == location_id)
        .order_by(LocationCapacityRule.reservation_type)
    )
    return list(result.scalars().all())


async def get_capacity_rule(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    rule_id: uuid.UUID,
) -> LocationCapacityRule | None:
    """Fetch a single capacity rule ensuring tenancy."""
    result = await session.execute(
        select(LocationCapacityRule)
        .join(Location)
        .where(LocationCapacityRule.id == rule_id, Location.account_id == account_id)
    )
    return result.scalar_one_or_none()


async def create_capacity_rule(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
    reservation_type: ReservationType,
    max_active: int | None,
    waitlist_limit: int | None,
) -> LocationCapacityRule:
    """Create a new capacity rule for a location."""
    await _ensure_location_access(session, account_id=account_id, location_id=location_id)
    rule = LocationCapacityRule(
        location_id=location_id,
        reservation_type=reservation_type,
        max_active=max_active,
        waitlist_limit=waitlist_limit,
    )
    session.add(rule)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(rule)
    return rule


async def update_capacity_rule(
    session: AsyncSession,
    *,
    rule: LocationCapacityRule,
    account_id: uuid.UUID,
    max_active: int | None,
    waitlist_limit: int | None,
) -> LocationCapacityRule:
    """Update an existing capacity rule."""
    await _ensure_location_access(session, account_id=account_id, location_id=rule.location_id)
    rule.max_active = max_active
    rule.waitlist_limit = waitlist_limit
    await session.commit()
    await session.refresh(rule)
    return rule


async def delete_capacity_rule(
    session: AsyncSession,
    *,
    rule: LocationCapacityRule,
    account_id: uuid.UUID,
) -> None:
    """Remove a capacity rule."""
    await _ensure_location_access(session, account_id=account_id, location_id=rule.location_id)
    await session.delete(rule)
    await session.commit()


async def _ensure_location_access(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    location_id: uuid.UUID,
) -> Location:
    location = await session.get(Location, location_id)
    if location is None or location.account_id != account_id:
        raise ValueError("Location does not belong to the provided account")
    return location
