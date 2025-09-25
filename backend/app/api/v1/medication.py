"""Medication schedule API endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.medication import (
    MedicationScheduleCreate,
    MedicationScheduleRead,
    MedicationScheduleUpdate,
)
from app.services import medication_service

router = APIRouter(prefix="/reservations/{reservation_id}/medication-schedules")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("", response_model=list[MedicationScheduleRead], summary="List medication schedules")
async def list_medication_schedules(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[MedicationScheduleRead]:
    _assert_staff(current_user)
    try:
        schedules = await medication_service.list_medication_schedules(
            session,
            account_id=current_user.account_id,
            reservation_id=reservation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [MedicationScheduleRead.model_validate(obj) for obj in schedules]


@router.post(
    "",
    response_model=MedicationScheduleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create medication schedule",
)
async def create_medication_schedule(
    reservation_id: uuid.UUID,
    payload: MedicationScheduleCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> MedicationScheduleRead:
    _assert_staff(current_user)
    if payload.reservation_id != reservation_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation mismatch")
    try:
        schedule = await medication_service.create_medication_schedule(
            session,
            payload,
            account_id=current_user.account_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return MedicationScheduleRead.model_validate(schedule)


@router.patch(
    "/{schedule_id}",
    response_model=MedicationScheduleRead,
    summary="Update medication schedule",
)
async def update_medication_schedule(
    reservation_id: uuid.UUID,
    schedule_id: uuid.UUID,
    payload: MedicationScheduleUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> MedicationScheduleRead:
    _assert_staff(current_user)
    schedule = await medication_service.get_medication_schedule(
        session,
        account_id=current_user.account_id,
        schedule_id=schedule_id,
    )
    if schedule is None or schedule.reservation_id != reservation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication schedule not found")
    try:
        updated = await medication_service.update_medication_schedule(
            session,
            schedule=schedule,
            account_id=current_user.account_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MedicationScheduleRead.model_validate(updated)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete medication schedule",
)
async def delete_medication_schedule(
    reservation_id: uuid.UUID,
    schedule_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    schedule = await medication_service.get_medication_schedule(
        session,
        account_id=current_user.account_id,
        schedule_id=schedule_id,
    )
    if schedule is None or schedule.reservation_id != reservation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication schedule not found")
    await medication_service.delete_medication_schedule(
        session,
        schedule=schedule,
        account_id=current_user.account_id,
    )
