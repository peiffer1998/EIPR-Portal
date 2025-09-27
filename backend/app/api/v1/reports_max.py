"""CSV reporting endpoints for Phase 16."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date
from typing import Annotated, Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models import ReservationType
from app.models.user import User, UserRole
from app.services import reports_max_service as service

router = APIRouter(prefix="/reports-max")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


def _to_csv_stream(rows: list[list[str]]) -> Iterable[str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow(row)
        yield buffer.getvalue()


def _csv_response(rows: list[list[str]]) -> StreamingResponse:
    return StreamingResponse(_to_csv_stream(rows), media_type="text/csv")


@router.get("/revenue-by-date.csv", summary="Revenue totals grouped by date")
async def revenue_by_date_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
    location_id: uuid.UUID | None = Query(default=None),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.revenue_by_date(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
            location_id=location_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/sales-tax-by-date.csv", summary="Sales tax collected per day")
async def sales_tax_by_date_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
    location_id: uuid.UUID | None = Query(default=None),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.sales_tax_by_date(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
            location_id=location_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/payments-by-method.csv", summary="Payments grouped by provider/status")
async def payments_by_method_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.payments_by_method(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/discounts-by-date.csv", summary="Discount totals per day")
async def discounts_by_date_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.discounts_by_date(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/deposits.csv", summary="Deposit activity")
async def deposits_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.deposits_summary(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/open-invoices-aging.csv", summary="Outstanding invoices aging buckets")
async def invoices_aging_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    as_of: date = Query(...),
) -> StreamingResponse:
    _assert_staff(current_user)
    rows = await service.invoices_aging(
        session,
        account_id=current_user.account_id,
        as_of=as_of,
    )
    return _csv_response(rows)


@router.get("/new-vs-repeat.csv", summary="New vs repeat customers")
async def new_vs_repeat_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.new_vs_repeat_customers(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/reservations-status.csv", summary="Reservation status counts")
async def reservations_status_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
    location_id: uuid.UUID | None = Query(default=None),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.reservations_status_summary(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
            location_id=location_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/occupancy.csv", summary="Occupancy CSV export")
async def occupancy_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
    location_id: uuid.UUID | None = Query(default=None),
    reservation_type: ReservationType | None = Query(default=None),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.occupancy_csv(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
            location_id=location_id,
            reservation_type=reservation_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/grooming-commissions.csv", summary="Grooming commissions totals")
async def grooming_commissions_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
    specialist_id: uuid.UUID | None = Query(default=None),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.grooming_commissions_csv(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
            specialist_id=specialist_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/tips-by-user-and-day.csv", summary="Tip totals per user")
async def tips_by_user_and_day_csv(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    date_from: date = Query(..., alias="date_from"),
    date_to: date = Query(..., alias="date_to"),
) -> StreamingResponse:
    _assert_staff(current_user)
    try:
        rows = await service.tips_by_user_and_day(
            session,
            account_id=current_user.account_id,
            start_date=date_from,
            end_date=date_to,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _csv_response(rows)


@router.get("/gift-certificates.csv", summary="Gift certificates report placeholder")
async def gift_certificates_csv() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "Not implemented in this build"},
    )


@router.get("/packages.csv", summary="Packages report placeholder")
async def packages_csv() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "Not implemented in this build"},
    )


@router.get("/store-credit-ledger.csv", summary="Store credit report placeholder")
async def store_credit_csv() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "Not implemented in this build"},
    )
