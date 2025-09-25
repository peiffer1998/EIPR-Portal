"""Account administration API endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.services import account_service

router = APIRouter()


def _require_account_admin(user: User) -> None:
    if user.role not in {UserRole.SUPERADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("", response_model=list[AccountRead], summary="List accounts")
async def list_accounts(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    skip: int = 0,
    limit: int = 50,
) -> list[AccountRead]:
    _require_account_admin(current_user)
    if current_user.role == UserRole.SUPERADMIN:
        accounts = await account_service.list_accounts(session, skip=skip, limit=limit)
    else:
        account = await account_service.get_account(session, current_user.account_id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
        accounts = [account]
    return [AccountRead.model_validate(obj) for obj in accounts]


@router.post(
    "",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create account",
)
async def create_account(
    payload: AccountCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> AccountRead:
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only superadmins can create accounts")
    try:
        account = await account_service.create_account(session, payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account slug already in use") from exc
    return AccountRead.model_validate(account)


@router.get("/{account_id}", response_model=AccountRead, summary="Get account")
async def read_account(
    account_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> AccountRead:
    _require_account_admin(current_user)
    account = await account_service.get_account(session, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if current_user.role != UserRole.SUPERADMIN and account.id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return AccountRead.model_validate(account)


@router.patch("/{account_id}", response_model=AccountRead, summary="Update account")
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> AccountRead:
    _require_account_admin(current_user)
    account = await account_service.get_account(session, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if current_user.role != UserRole.SUPERADMIN and account.id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    try:
        updated = await account_service.update_account(session, account, payload)
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account slug already in use") from exc
    return AccountRead.model_validate(updated)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account",
)
async def delete_account(
    account_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _require_account_admin(current_user)
    account = await account_service.get_account(session, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if current_user.role != UserRole.SUPERADMIN and account.id != current_user.account_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    await account_service.delete_account(session, account)
