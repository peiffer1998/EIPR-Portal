"""Location administration API endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.location import LocationCreate, LocationRead, LocationUpdate
from app.services import location_service

router = APIRouter()


def _require_location_admin(user: User) -> None:
    if user.role not in {UserRole.SUPERADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("", response_model=list[LocationRead], summary="List locations")
async def list_locations(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    account_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[LocationRead]:
    _require_location_admin(current_user)
    target_account = account_id
    if current_user.role != UserRole.SUPERADMIN:
        if account_id is not None and account_id != current_user.account_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other accounts")
        target_account = current_user.account_id
    locations = await location_service.list_locations(
        session,
        account_id=target_account,
        skip=skip,
        limit=limit,
    )
    return [LocationRead.model_validate(obj) for obj in locations]


@router.post(
    "",
    response_model=LocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create location",
)
async def create_location(
    payload: LocationCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> LocationRead:
    _require_location_admin(current_user)
    if current_user.role != UserRole.SUPERADMIN and payload.account_id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account mismatch")
    try:
        location = await location_service.create_location(session, payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location already exists") from exc
    return LocationRead.model_validate(location)


@router.get(
    "/{location_id}",
    response_model=LocationRead,
    summary="Get location",
)
async def read_location(
    location_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> LocationRead:
    _require_location_admin(current_user)
    account_scope = None if current_user.role == UserRole.SUPERADMIN else current_user.account_id
    location = await location_service.get_location(
        session,
        location_id=location_id,
        account_id=account_scope,
    )
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return LocationRead.model_validate(location)


@router.patch(
    "/{location_id}",
    response_model=LocationRead,
    summary="Update location",
)
async def update_location(
    location_id: uuid.UUID,
    payload: LocationUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> LocationRead:
    _require_location_admin(current_user)
    account_scope = None if current_user.role == UserRole.SUPERADMIN else current_user.account_id
    location = await location_service.get_location(
        session,
        location_id=location_id,
        account_id=account_scope,
    )
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    updated = await location_service.update_location(session, location, payload)
    return LocationRead.model_validate(updated)


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete location",
)
async def delete_location(
    location_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _require_location_admin(current_user)
    account_scope = None if current_user.role == UserRole.SUPERADMIN else current_user.account_id
    location = await location_service.get_location(
        session,
        location_id=location_id,
        account_id=account_scope,
    )
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    await location_service.delete_location(session, location)
