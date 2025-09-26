"""Commission payout endpoints."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models import CommissionPayout, User, UserRole
from app.schemas.payroll import CommissionPayoutRead
from app.services import commission_service

router = APIRouter()


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.post(
    "/commissions/build", summary="Build commission payouts from completed appointments"
)
async def build_commissions(
    date_from: date,
    date_to: date,
    location_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> dict[str, int]:
    _assert_staff(current_user)
    if date_from > date_to:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="date_from must be on or before date_to"
        )
    created = await commission_service.build_from_completed_appointments(
        session,
        account_id=current_user.account_id,
        date_from=date_from,
        date_to=date_to,
        location_id=location_id,
    )
    return {"created": created}


@router.get(
    "/commissions",
    response_model=list[CommissionPayoutRead],
    summary="List commission payouts",
)
async def list_commissions(
    specialist_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(deps.get_db_session),
    current_user: User = Depends(deps.get_current_active_user),
) -> list[CommissionPayoutRead]:
    _assert_staff(current_user)
    stmt = select(CommissionPayout).where(
        CommissionPayout.account_id == current_user.account_id
    )
    if specialist_id:
        stmt = stmt.where(CommissionPayout.specialist_id == specialist_id)
    payouts = (await session.execute(stmt)).scalars().all()
    return [CommissionPayoutRead.model_validate(p) for p in payouts]
