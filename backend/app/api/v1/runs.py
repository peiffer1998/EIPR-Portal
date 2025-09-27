"""Lodging run endpoints for boarding assignments."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.lodging import LodgingType
from app.models.user import User, UserRole
from app.schemas.lodging import RunRead

router = APIRouter(prefix="/runs", tags=["runs"])


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get(
    "",
    response_model=list[RunRead],
    summary="List lodging runs for the current account",
)
async def list_runs_endpoint(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    location_id: str | None = Query(default=None),
) -> list[RunRead]:
    """Return lodging runs (kennels/rooms) for drag-drop assignments."""

    _assert_staff(current_user)

    stmt = select(LodgingType).where(LodgingType.account_id == current_user.account_id)
    if location_id:
        try:
            loc_uuid = uuid.UUID(location_id)
        except ValueError:
            loc_uuid = None
        if loc_uuid is not None:
            stmt = stmt.where(LodgingType.location_id == loc_uuid)

    result = await session.execute(stmt.order_by(LodgingType.created_at.asc()))
    runs = list(result.scalars().all())

    if not runs:
        return [
            RunRead(id="ROOM", name="Rooms", kind="room", capacity=None),
            RunRead(id="SUITE", name="Suites", kind="suite", capacity=None),
        ]

    items: list[RunRead] = []
    for run in runs:
        items.append(
            RunRead(
                id=str(run.id),
                name=run.name,
                kind="room",
                capacity=None,
            )
        )
    return items
