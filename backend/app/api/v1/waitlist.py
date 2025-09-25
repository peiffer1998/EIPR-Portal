"""Waitlist endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.waitlist_entry import WaitlistStatus
from app.models.user import User, UserRole
from app.schemas.waitlist import WaitlistEntryCreate, WaitlistEntryRead, WaitlistStatusUpdate
from app.services import waitlist_service

router = APIRouter(prefix="/waitlist")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("", response_model=list[WaitlistEntryRead], summary="List waitlist entries")
async def list_waitlist_entries(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    status_filter: WaitlistStatus | None = Query(default=None, alias="status"),
) -> list[WaitlistEntryRead]:
    _assert_staff(current_user)
    entries = await waitlist_service.list_entries(
        session,
        account_id=current_user.account_id,
        status=status_filter,
    )
    return [WaitlistEntryRead.model_validate(entry) for entry in entries]


@router.post("", response_model=WaitlistEntryRead, status_code=status.HTTP_201_CREATED, summary="Create waitlist entry")
async def create_waitlist_entry(
    payload: WaitlistEntryCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> WaitlistEntryRead:
    _assert_staff(current_user)
    try:
        entry = await waitlist_service.create_entry(
            session,
            account_id=current_user.account_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WaitlistEntryRead.model_validate(entry)


@router.patch("/{entry_id}", response_model=WaitlistEntryRead, summary="Update waitlist status")
async def update_waitlist_entry(
    entry_id: uuid.UUID,
    payload: WaitlistStatusUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> WaitlistEntryRead:
    _assert_staff(current_user)
    entry = await waitlist_service.get_entry(
        session,
        account_id=current_user.account_id,
        entry_id=entry_id,
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found")
    updated = await waitlist_service.update_entry_status(session, entry=entry, payload=payload)
    return WaitlistEntryRead.model_validate(updated)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove waitlist entry")
async def delete_waitlist_entry(
    entry_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff(current_user)
    entry = await waitlist_service.get_entry(
        session,
        account_id=current_user.account_id,
        entry_id=entry_id,
    )
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found")
    await waitlist_service.delete_entry(session, entry=entry)
    return None
