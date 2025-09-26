"""Reservation deposit endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.deposit import DepositActionRequest, DepositRead
from app.services import invoice_service

router = APIRouter(prefix="/reservations/{reservation_id}/deposits", tags=["deposits"])


def _require_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


async def _settle(
    session: AsyncSession,
    *,
    reservation_id: UUID,
    account_id: UUID,
    action: str,
    amount: Decimal,
):
    try:
        return await invoice_service.settle_deposit(
            session,
            reservation_id=reservation_id,
            account_id=account_id,
            action=action,
            amount=amount,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/hold", response_model=DepositRead, status_code=status.HTTP_201_CREATED)
async def hold_deposit(
    reservation_id: UUID,
    payload: DepositActionRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> DepositRead:
    _require_staff(current_user)
    deposit = await _settle(
        session,
        reservation_id=reservation_id,
        account_id=current_user.account_id,
        action="hold",
        amount=payload.amount,
    )
    return DepositRead.model_validate(deposit)


@router.post("/consume", response_model=DepositRead)
async def consume_deposit(
    reservation_id: UUID,
    payload: DepositActionRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> DepositRead:
    _require_staff(current_user)
    deposit = await _settle(
        session,
        reservation_id=reservation_id,
        account_id=current_user.account_id,
        action="consume",
        amount=payload.amount,
    )
    return DepositRead.model_validate(deposit)


@router.post("/refund", response_model=DepositRead)
async def refund_deposit(
    reservation_id: UUID,
    payload: DepositActionRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> DepositRead:
    _require_staff(current_user)
    deposit = await _settle(
        session,
        reservation_id=reservation_id,
        account_id=current_user.account_id,
        action="refund",
        amount=payload.amount,
    )
    return DepositRead.model_validate(deposit)


@router.post("/forfeit", response_model=DepositRead)
async def forfeit_deposit(
    reservation_id: UUID,
    payload: DepositActionRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> DepositRead:
    _require_staff(current_user)
    deposit = await _settle(
        session,
        reservation_id=reservation_id,
        account_id=current_user.account_id,
        action="forfeit",
        amount=payload.amount,
    )
    return DepositRead.model_validate(deposit)
