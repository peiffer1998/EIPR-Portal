"""Payroll period endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User, UserRole
from app.schemas.payroll import PayrollPeriodCreate, PayrollPeriodRead
from app.services import payroll_service

router = APIRouter()


def _assert_manager(user: User) -> None:
    if user.role not in (UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.post(
    "/payroll/periods",
    response_model=PayrollPeriodRead,
    status_code=status.HTTP_201_CREATED,
    summary="Open payroll period",
)
async def create_period(
    payload: PayrollPeriodCreate,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> PayrollPeriodRead:
    _assert_manager(current_user)
    period = await payroll_service.open_period(
        session,
        account_id=current_user.account_id,
        location_id=payload.location_id,
        starts_on=payload.starts_on,
        ends_on=payload.ends_on,
    )
    return PayrollPeriodRead.model_validate(period)


@router.post(
    "/payroll/periods/{period_id}/lock",
    response_model=PayrollPeriodRead,
    summary="Lock payroll period",
)
async def lock_period(
    period_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> PayrollPeriodRead:
    _assert_manager(current_user)
    try:
        period = await payroll_service.lock_period(
            session,
            account_id=current_user.account_id,
            period_id=period_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PayrollPeriodRead.model_validate(period)


@router.post(
    "/payroll/periods/{period_id}/mark-paid",
    response_model=PayrollPeriodRead,
    summary="Mark payroll period paid",
)
async def mark_paid(
    period_id: uuid.UUID,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> PayrollPeriodRead:
    _assert_manager(current_user)
    try:
        period = await payroll_service.mark_paid(
            session,
            account_id=current_user.account_id,
            period_id=period_id,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PayrollPeriodRead.model_validate(period)
