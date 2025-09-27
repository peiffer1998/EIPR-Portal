"""Location hours and closures endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.location_hours import LocationClosure, LocationHour
from app.models.user import User, UserRole
from app.schemas.location_hours import (
    LocationClosureCreate,
    LocationClosureRead,
    LocationHourCreate,
    LocationHourRead,
    LocationHourUpdate,
)
from app.services import location_hours_service

router = APIRouter(prefix="/locations/{location_id}")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get(
    "/hours", response_model=list[LocationHourRead], summary="List weekly hours"
)
async def list_location_hours(
    location_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[LocationHourRead]:
    _assert_staff(current_user)
    hours = await location_hours_service.list_hours(
        session,
        account_id=current_user.account_id,
        location_id=location_id,
    )
    return [LocationHourRead.model_validate(hour) for hour in hours]


@router.put("/hours", response_model=LocationHourRead, summary="Upsert weekly hour")
async def upsert_location_hour(
    location_id: uuid.UUID,
    payload: LocationHourCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> LocationHourRead:
    _assert_staff(current_user)
    try:
        hour = await location_hours_service.upsert_hour(
            session,
            account_id=current_user.account_id,
            location_id=location_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return LocationHourRead.model_validate(hour)


@router.patch(
    "/hours/{hour_id}", response_model=LocationHourRead, summary="Update location hour"
)
async def update_location_hour(
    location_id: uuid.UUID,
    hour_id: uuid.UUID,
    payload: LocationHourUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> LocationHourRead:
    _assert_staff(current_user)
    hour = await session.get(LocationHour, hour_id)
    if hour is None or hour.location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hour not found"
        )
    try:
        updated = await location_hours_service.update_hour(
            session, hour=hour, payload=payload
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return LocationHourRead.model_validate(updated)


@router.delete(
    "/hours/{hour_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete location hour",
)
async def delete_location_hour(
    location_id: uuid.UUID,
    hour_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    hour = await session.get(LocationHour, hour_id)
    if hour is None or hour.location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hour not found"
        )
    await location_hours_service.delete_hour(session, hour=hour)
    return None


@router.get(
    "/closures", response_model=list[LocationClosureRead], summary="List closures"
)
async def list_location_closures(
    location_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[LocationClosureRead]:
    _assert_staff(current_user)
    closures = await location_hours_service.list_closures(
        session,
        account_id=current_user.account_id,
        location_id=location_id,
    )
    return [LocationClosureRead.model_validate(closure) for closure in closures]


@router.post(
    "/closures",
    response_model=LocationClosureRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create closure",
)
async def create_location_closure(
    location_id: uuid.UUID,
    payload: LocationClosureCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> LocationClosureRead:
    _assert_staff(current_user)
    try:
        closure = await location_hours_service.create_closure(
            session,
            account_id=current_user.account_id,
            location_id=location_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return LocationClosureRead.model_validate(closure)


@router.delete(
    "/closures/{closure_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete closure",
)
async def delete_location_closure(
    location_id: uuid.UUID,
    closure_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    closure = await session.get(LocationClosure, closure_id)
    if closure is None or closure.location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Closure not found"
        )
    await location_hours_service.delete_closure(session, closure=closure)
    return None
