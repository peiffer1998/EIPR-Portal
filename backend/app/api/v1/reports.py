"""Reporting and analytics endpoints."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.reservation import ReservationType
from app.models.user import User, UserRole
from app.schemas.reporting import OccupancyEntry, RevenueEntry, RevenueReport
from app.services import reporting_service

router = APIRouter(prefix="/reports")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/occupancy", response_model=list[OccupancyEntry], summary="Daily occupancy report")
async def occupancy_report(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    start_date: date = Query(...),
    end_date: date = Query(...),
    location_id: uuid.UUID | None = Query(default=None),
    reservation_type: ReservationType | None = Query(default=None),
) -> list[OccupancyEntry]:
    _assert_staff(current_user)
    try:
        entries = await reporting_service.occupancy_report(
            session,
            account_id=current_user.account_id,
            start_date=start_date,
            end_date=end_date,
            location_id=location_id,
            reservation_type=reservation_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [OccupancyEntry.model_validate(entry) for entry in entries]


@router.get("/revenue", response_model=RevenueReport, summary="Revenue report")
async def revenue_report(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    start_date: date = Query(...),
    end_date: date = Query(...),
    location_id: uuid.UUID | None = Query(default=None),
) -> RevenueReport:
    _assert_staff(current_user)
    try:
        report = await reporting_service.revenue_report(
            session,
            account_id=current_user.account_id,
            start_date=start_date,
            end_date=end_date,
            location_id=location_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    entries = [RevenueEntry.model_validate(entry) for entry in report["entries"]]
    return RevenueReport(entries=entries, grand_total=report["grand_total"])
