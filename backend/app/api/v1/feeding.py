"""Feeding schedule API endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.feeding import (
    FeedingScheduleCreate,
    FeedingScheduleRead,
    FeedingScheduleUpdate,
)
from app.services import feeding_service

router = APIRouter(prefix="/reservations/{reservation_id}/feeding-schedules")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("", response_model=list[FeedingScheduleRead], summary="List feeding schedules")
async def list_feeding_schedules(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[FeedingScheduleRead]:
    _assert_staff(current_user)
    try:
        schedules = await feeding_service.list_feeding_schedules(
            session,
            account_id=current_user.account_id,
            reservation_id=reservation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [FeedingScheduleRead.model_validate(obj) for obj in schedules]


@router.post(
    "",
    response_model=FeedingScheduleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create feeding schedule",
)
async def create_feeding_schedule(
    reservation_id: uuid.UUID,
    payload: FeedingScheduleCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> FeedingScheduleRead:
    _assert_staff(current_user)
    if payload.reservation_id != reservation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation mismatch")
    try:
        schedule = await feeding_service.create_feeding_schedule(
            session,
            payload,
            account_id=current_user.account_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FeedingScheduleRead.model_validate(schedule)


@router.patch(
    "/{schedule_id}",
    response_model=FeedingScheduleRead,
    summary="Update feeding schedule",
)
async def update_feeding_schedule(
    reservation_id: uuid.UUID,
    schedule_id: uuid.UUID,
    payload: FeedingScheduleUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> FeedingScheduleRead:
    _assert_staff(current_user)
    schedule = await feeding_service.get_feeding_schedule(
        session,
        account_id=current_user.account_id,
        schedule_id=schedule_id,
    )
    if schedule is None or schedule.reservation_id != reservation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeding schedule not found")
    try:
        updated = await feeding_service.update_feeding_schedule(
            session,
            schedule=schedule,
            account_id=current_user.account_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FeedingScheduleRead.model_validate(updated)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete feeding schedule",
)
async def delete_feeding_schedule(
    reservation_id: uuid.UUID,
    schedule_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    schedule = await feeding_service.get_feeding_schedule(
        session,
        account_id=current_user.account_id,
        schedule_id=schedule_id,
    )
    if schedule is None or schedule.reservation_id != reservation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feeding schedule not found")
    await feeding_service.delete_feeding_schedule(
        session,
        schedule=schedule,
        account_id=current_user.account_id,
    )
