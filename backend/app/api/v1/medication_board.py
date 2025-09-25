"""Endpoints for aggregated medication schedules."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.ops_p5 import MedicationBoardRow
from app.services import medication_board_service

router = APIRouter()


def _require_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get(
    "/today",
    response_model=list[MedicationBoardRow],
    summary="List today's medication schedules for a location",
)
async def medication_today(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    location_id: uuid.UUID = Query(..., description="Location identifier"),
) -> list[MedicationBoardRow]:
    _require_staff(current_user)
    try:
        rows = await medication_board_service.list_today(
            session,
            account_id=current_user.account_id,
            location_id=location_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return rows
