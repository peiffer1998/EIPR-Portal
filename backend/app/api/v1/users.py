"""User management endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead
from app.services import user_service

router = APIRouter()


def _assert_manage_users_permission(user: User) -> None:
    """Ensure the user can manage other accounts."""
    if user.role not in {UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/me", response_model=UserRead, summary="Current user profile")
async def read_current_user(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> UserRead:
    """Return the authenticated user's profile."""
    return UserRead.model_validate(current_user)


@router.get("", response_model=list[UserRead], summary="List users")
async def list_users(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    skip: int = 0,
    limit: int = 50,
) -> list[UserRead]:
    """Return paginated users for the current account."""
    _assert_manage_users_permission(current_user)
    users = await user_service.list_users(session, skip=skip, limit=min(limit, 100))
    return [UserRead.model_validate(obj) for obj in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Create user")
async def create_user(
    payload: UserCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> UserRead:
    """Create a new user within the same account."""
    _assert_manage_users_permission(current_user)
    if payload.account_id != current_user.account_id and current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account mismatch")
    try:
        user = await user_service.create_user(session, payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use") from exc
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead, summary="Get user by ID")
async def read_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> UserRead:
    """Fetch a user by identifier."""
    _assert_manage_users_permission(current_user)
    user = await user_service.get_user(session, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.account_id != current_user.account_id and current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)
