"""User management endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.user import (
    StaffInvitationCreate,
    StaffInvitationRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services import notification_service, staff_invitation_service, user_service

router = APIRouter()

_ROLE_PRIORITY: dict[UserRole, int] = {
    UserRole.SUPERADMIN: 5,
    UserRole.ADMIN: 4,
    UserRole.MANAGER: 3,
    UserRole.STAFF: 2,
    UserRole.PET_PARENT: 1,
}


def _assert_manage_users_permission(user: User) -> None:
    """Ensure the user can manage other accounts."""
    if user.role not in {UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


def _assert_assignable_role(actor: User, target_role: UserRole) -> None:
    if actor.role == UserRole.SUPERADMIN:
        return
    if _ROLE_PRIORITY[target_role] > _ROLE_PRIORITY[actor.role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign higher role"
        )


def _assert_can_manage_target(actor: User, target: User) -> None:
    if actor.role == UserRole.SUPERADMIN:
        return
    if actor.account_id != target.account_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if target.id == actor.id:
        return
    if _ROLE_PRIORITY[target.role] >= _ROLE_PRIORITY[actor.role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


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
    users = await user_service.list_users(
        session,
        account_id=current_user.account_id,
        skip=skip,
        limit=min(limit, 100),
    )
    return [UserRead.model_validate(obj) for obj in users]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
async def create_user(
    payload: UserCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> UserRead:
    """Create a new user within the same account."""
    _assert_manage_users_permission(current_user)
    if (
        payload.account_id != current_user.account_id
        and current_user.role != UserRole.SUPERADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account mismatch"
        )
    _assert_assignable_role(current_user, payload.role)
    try:
        user = await user_service.create_user(session, payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
        ) from exc
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if (
        current_user.role != UserRole.SUPERADMIN
        and user.account_id != current_user.account_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead, summary="Update user")
async def update_user_endpoint(
    user_id: uuid.UUID,
    payload: UserUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> UserRead:
    _assert_manage_users_permission(current_user)
    user = await user_service.get_user(session, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    _assert_can_manage_target(current_user, user)
    if payload.role is not None:
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change own role"
            )
        _assert_assignable_role(current_user, payload.role)
    try:
        updated = await user_service.update_user(session, user, payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to update user"
        ) from exc
    return UserRead.model_validate(updated)


@router.get(
    "/invitations",
    response_model=list[StaffInvitationRead],
    summary="List pending staff invitations",
)
async def list_staff_invitations(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> list[StaffInvitationRead]:
    _assert_manage_users_permission(current_user)
    invitations = await staff_invitation_service.list_invitations(
        session,
        account_id=current_user.account_id,
    )
    return [StaffInvitationRead.model_validate(inv) for inv in invitations]


@router.post(
    "/invitations",
    response_model=StaffInvitationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Invite staff member",
)
async def invite_staff_member(
    payload: StaffInvitationCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
) -> StaffInvitationRead:
    _assert_manage_users_permission(current_user)
    _assert_assignable_role(current_user, payload.role)
    try:
        invitation, raw_token = await staff_invitation_service.create_invitation(
            session,
            account_id=current_user.account_id,
            invited_by_user_id=current_user.id,
            payload=payload,
            expires_in_hours=payload.expires_in_hours,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    inviter_name = f"{current_user.first_name} {current_user.last_name}".strip()
    subject, body = notification_service.build_staff_invitation_email(
        first_name=payload.first_name,
        inviter_name=inviter_name,
        role=payload.role.value.replace("_", " "),
        token=raw_token,
    )
    notification_service.schedule_email(
        background_tasks,
        recipients=[payload.email],
        subject=subject,
        body=body,
    )

    invitation_read = StaffInvitationRead.model_validate(invitation)
    return invitation_read.model_copy(update={"invite_token": raw_token})
