"""Reservation management API."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.reservation import ReservationCreate, ReservationRead, ReservationUpdate
from app.services import reservation_service

router = APIRouter()


def _assert_staff_authority(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("", response_model=list[ReservationRead], summary="List reservations")
async def list_reservations(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    skip: int = 0,
    limit: int = 50,
) -> list[ReservationRead]:
    _assert_staff_authority(current_user)
    reservations = await reservation_service.list_reservations(
        session,
        account_id=current_user.account_id,
        skip=skip,
        limit=min(limit, 100),
    )
    return [ReservationRead.model_validate(obj) for obj in reservations]


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED, summary="Create reservation")
async def create_reservation(
    payload: ReservationCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReservationRead:
    _assert_staff_authority(current_user)
    try:
        reservation = await reservation_service.create_reservation(
            session,
            account_id=current_user.account_id,
            **payload.model_dump(),
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to create reservation") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ReservationRead.model_validate(reservation)


@router.get("/{reservation_id}", response_model=ReservationRead, summary="Get reservation")
async def get_reservation(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReservationRead:
    _assert_staff_authority(current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    return ReservationRead.model_validate(reservation)


@router.patch("/{reservation_id}", response_model=ReservationRead, summary="Update reservation")
async def update_reservation(
    reservation_id: uuid.UUID,
    payload: ReservationUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReservationRead:
    _assert_staff_authority(current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    try:
        updated = await reservation_service.update_reservation(
            session,
            reservation=reservation,
            account_id=current_user.account_id,
            **payload.model_dump(exclude_unset=True),
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to update reservation") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ReservationRead.model_validate(updated)


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete reservation")
async def delete_reservation(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff_authority(current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    try:
        await reservation_service.delete_reservation(
            session,
            reservation=reservation,
            account_id=current_user.account_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
