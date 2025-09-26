"""Waitlist management endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.models.waitlist_entry import WaitlistServiceType, WaitlistStatus
from app.schemas.reservation import ReservationRead
from app.schemas.waitlist import (
    WaitlistEntryCreate,
    WaitlistEntryRead,
    WaitlistEntryUpdate,
    WaitlistListResponse,
    WaitlistOfferRequest,
    WaitlistOfferResponse,
    WaitlistPromoteRequest,
)
from app.services import waitlist_service

router = APIRouter(prefix="/waitlist")


def _require_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


def _require_manager(user: User) -> None:
    if user.role not in {UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPERADMIN}:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Manager permissions required"
        )


@router.get("", response_model=WaitlistListResponse, summary="List waitlist entries")
async def list_waitlist_entries(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    location_id: uuid.UUID | None = Query(default=None),
    service_type: WaitlistServiceType | None = Query(default=None),
    status_filter: WaitlistStatus | None = Query(default=None, alias="status"),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
) -> WaitlistListResponse:
    _require_staff(current_user)
    try:
        entries, next_cursor = await waitlist_service.list_entries(
            session,
            account_id=current_user.account_id,
            location_id=location_id,
            service_type=service_type,
            status=status_filter,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WaitlistListResponse(
        entries=[WaitlistEntryRead.from_orm_entry(entry) for entry in entries],
        next_cursor=next_cursor,
    )


@router.post(
    "",
    response_model=WaitlistEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create waitlist entry",
)
async def create_waitlist_entry(
    payload: WaitlistEntryCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> WaitlistEntryRead:
    _require_staff(current_user)
    try:
        entry = await waitlist_service.add_entry(
            session,
            account_id=current_user.account_id,
            user_id=current_user.id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WaitlistEntryRead.from_orm_entry(entry)


@router.patch(
    "/{entry_id}", response_model=WaitlistEntryRead, summary="Update waitlist entry"
)
async def update_waitlist_entry(
    entry_id: uuid.UUID,
    payload: WaitlistEntryUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> WaitlistEntryRead:
    _require_manager(current_user)
    entry = await waitlist_service.get_entry(
        session,
        account_id=current_user.account_id,
        entry_id=entry_id,
    )
    if entry is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found"
        )
    try:
        updated = await waitlist_service.update_entry(
            session,
            entry=entry,
            payload=payload,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WaitlistEntryRead.from_orm_entry(updated)


@router.post(
    "/{entry_id}/offer",
    response_model=WaitlistOfferResponse,
    summary="Offer waitlist entry",
)
async def offer_waitlist_entry(
    entry_id: uuid.UUID,
    payload: WaitlistOfferRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
) -> WaitlistOfferResponse:
    _require_manager(current_user)
    entry = await waitlist_service.get_entry(
        session,
        account_id=current_user.account_id,
        entry_id=entry_id,
    )
    if entry is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found"
        )
    if not payload.sent_to:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Destination required for offer"
        )
    try:
        response = await waitlist_service.offer_entry(
            session,
            entry=entry,
            user_id=current_user.id,
            payload=payload,
            background_tasks=background_tasks,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return response


@router.post(
    "/{entry_id}/promote",
    response_model=list[ReservationRead],
    summary="Promote waitlist entry to confirmed",
)
async def promote_waitlist_entry(
    entry_id: uuid.UUID,
    payload: WaitlistPromoteRequest | None,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[ReservationRead]:
    _require_manager(current_user)
    entry = await waitlist_service.get_entry(
        session,
        account_id=current_user.account_id,
        entry_id=entry_id,
    )
    if entry is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found"
        )
    try:
        reservations = await waitlist_service.promote_entry(
            session,
            entry=entry,
            user_id=current_user.id,
            lodging_type_id=payload.lodging_type_id if payload else None,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [ReservationRead.model_validate(reservation) for reservation in reservations]
