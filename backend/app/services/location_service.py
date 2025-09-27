"""Location management services."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate


async def list_locations(
    session: AsyncSession,
    *,
    account_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Location]:
    """Return locations, optionally scoped to an account."""
    stmt: Select[tuple[Location]] = select(Location)
    if account_id is not None:
        stmt = stmt.where(Location.account_id == account_id)
    stmt = stmt.offset(skip).limit(min(limit, 100)).order_by(Location.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_location(
    session: AsyncSession,
    *,
    location_id: uuid.UUID,
    account_id: uuid.UUID | None = None,
) -> Location | None:
    """Fetch a location and optionally enforce account ownership."""
    location = await session.get(Location, location_id)
    if location is None:
        return None
    if account_id is not None and location.account_id != account_id:
        return None
    return location


async def create_location(session: AsyncSession, payload: LocationCreate) -> Location:
    """Create a new location."""
    location = Location(**payload.model_dump())
    session.add(location)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(location)
    return location


async def update_location(
    session: AsyncSession,
    location: Location,
    payload: LocationUpdate,
) -> Location:
    """Update mutable fields on a location."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    await session.commit()
    await session.refresh(location)
    return location


async def delete_location(session: AsyncSession, location: Location) -> None:
    """Delete a location."""
    await session.delete(location)
    await session.commit()
