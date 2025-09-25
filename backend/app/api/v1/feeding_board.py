"""Endpoints for aggregated feeding boards."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.reservation import ReservationType
from app.models.user import User, UserRole
from app.schemas.ops_p5 import FeedingBoardRow
from app.services import feeding_board_service

router = APIRouter()


def _require_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


def _coerce_service(service: str) -> ReservationType:
    try:
        service_type = ReservationType(service.lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported service",
        ) from exc
    if service_type not in {ReservationType.BOARDING, ReservationType.DAYCARE}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only daycare or boarding are supported",
        )
    return service_type


@router.get(
    "/today",
    response_model=list[FeedingBoardRow],
    summary="List today's feedings for a location",
)
async def feeding_today(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    location_id: uuid.UUID = Query(..., description="Location identifier"),
    service: str = Query(..., description="Service filter (daycare or boarding)"),
) -> list[FeedingBoardRow]:
    _require_staff(current_user)
    service_type = _coerce_service(service)
    try:
        rows = await feeding_board_service.list_today(
            session,
            account_id=current_user.account_id,
            location_id=location_id,
            service=service_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return rows
