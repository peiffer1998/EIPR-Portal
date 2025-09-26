"""Time clock endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.payroll import TimeClockPunchRead
from app.services import timeclock_service

router = APIRouter()


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.post(
    "/timeclock/punch-in",
    response_model=TimeClockPunchRead,
    status_code=status.HTTP_201_CREATED,
    summary="Punch in",
)
async def punch_in(
    location_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> TimeClockPunchRead:
    _assert_staff(current_user)
    try:
        punch = await timeclock_service.punch_in(
            session,
            account_id=current_user.account_id,
            location_id=location_id,
            user_id=current_user.id,
        )
    except ValueError as exc:  # duplicate open punch
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TimeClockPunchRead.model_validate(punch)


@router.post(
    "/timeclock/punch-out",
    response_model=TimeClockPunchRead,
    summary="Punch out",
)
async def punch_out(
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> TimeClockPunchRead:
    _assert_staff(current_user)
    try:
        punch = await timeclock_service.punch_out(
            session,
            account_id=current_user.account_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return TimeClockPunchRead.model_validate(punch)
