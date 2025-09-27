"""Reservation management API."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import RedirectResponse

from app.api import deps
from app.core.config import get_settings
from app.models.user import User, UserRole
from app.schemas.invoice import InvoiceRead
from app.schemas.reservation import (
    ReservationCheckInRequest,
    ReservationCheckOutRequest,
    ReservationCreate,
    ReservationMoveRunRequest,
    ReservationRead,
    ReservationUpdate,
)
from app.schemas.scheduling import (
    DailyAvailability,
    AvailabilityRequest,
    AvailabilityResponse,
)
from app.services import (
    billing_service,
    notification_service,
    reservation_service,
    waitlist_service,
)

router = APIRouter()

settings = get_settings()


def _assert_staff_authority(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get("", response_model=list[ReservationRead], summary="List reservations")
async def list_reservations(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    skip: int = 0,
    limit: int = 50,
) -> list[ReservationRead]:
    _assert_staff_authority(current_user)
    reservations = await reservation_service.list_reservations(
        session,
        account_id=current_user.account_id,
        skip=skip,
        limit=min(limit, 100),
    )
    return [ReservationRead.model_validate(obj) for obj in reservations]


@router.post(
    "",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create reservation",
)
async def create_reservation(
    payload: ReservationCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
) -> ReservationRead:
    _assert_staff_authority(current_user)
    try:
        reservation = await reservation_service.create_reservation(
            session,
            account_id=current_user.account_id,
            **payload.model_dump(),
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create reservation",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    notification_service.notify_booking_confirmation(reservation, background_tasks)
    return ReservationRead.model_validate(reservation)


@router.get(
    "/{reservation_id}", response_model=ReservationRead, summary="Get reservation"
)
async def get_reservation(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReservationRead:
    _assert_staff_authority(current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )
    return ReservationRead.model_validate(reservation)


@router.patch(
    "/{reservation_id}", response_model=ReservationRead, summary="Update reservation"
)
async def update_reservation(
    reservation_id: uuid.UUID,
    payload: ReservationUpdate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReservationRead:
    _assert_staff_authority(current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )
    try:
        updated = await reservation_service.update_reservation(
            session,
            reservation=reservation,
            account_id=current_user.account_id,
            **payload.model_dump(exclude_unset=True),
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to update reservation",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ReservationRead.model_validate(updated)


@router.post(
    "/{reservation_id}/move-run",
    response_model=ReservationRead,
    summary="Assign reservation to a lodging run",
)
async def move_reservation_run(
    reservation_id: uuid.UUID,
    payload: ReservationMoveRunRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> ReservationRead:
    _assert_staff_authority(current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )

    kennel_uuid: uuid.UUID | None
    if payload.run_id:
        try:
            kennel_uuid = uuid.UUID(payload.run_id)
        except ValueError:
            kennel_uuid = None
    else:
        kennel_uuid = None

    updated = await reservation_service.update_reservation(
        session,
        reservation=reservation,
        account_id=current_user.account_id,
        kennel_id=kennel_uuid,
    )
    return ReservationRead.model_validate(updated)


@router.post(
    "/{reservation_id}/check-in",
    response_model=ReservationRead,
    summary="Check in reservation",
)
async def check_in_reservation(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
    payload: ReservationCheckInRequest | None = None,
) -> ReservationRead:
    _assert_staff_authority(current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )
    payload = payload or ReservationCheckInRequest()
    check_in_at = payload.resolve_timestamp()
    try:
        updated = await reservation_service.check_in_reservation(
            session,
            reservation=reservation,
            account_id=current_user.account_id,
            check_in_at=check_in_at,
            kennel_id=payload.kennel_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    notification_service.notify_check_in(updated, background_tasks)
    return ReservationRead.model_validate(updated)


@router.post(
    "/{reservation_id}/check-out",
    response_model=ReservationRead,
    summary="Check out reservation",
)
async def check_out_reservation(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    payload: ReservationCheckOutRequest | None = None,
) -> ReservationRead:
    _assert_staff_authority(current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )
    payload = payload or ReservationCheckOutRequest()
    check_out_at = payload.resolve_timestamp()
    try:
        updated = await reservation_service.check_out_reservation(
            session,
            reservation=reservation,
            account_id=current_user.account_id,
            check_out_at=check_out_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ReservationRead.model_validate(updated)


@router.post(
    "/{reservation_id}/invoice",
    response_model=InvoiceRead,
    summary="Generate invoice for reservation",
)
async def generate_invoice(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
) -> InvoiceRead:
    _assert_staff_authority(current_user)
    try:
        invoice = await billing_service.generate_invoice_for_reservation(
            session,
            account_id=current_user.account_id,
            reservation_id=reservation_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    notification_service.notify_invoice_available(invoice, background_tasks)
    return InvoiceRead.model_validate(invoice)


@router.post(
    "/{reservation_id}/confirm",
    response_model=ReservationRead,
    summary="Confirm reservation by token",
)
async def confirm_reservation_by_token(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    token: str = Query(..., min_length=6),
) -> ReservationRead:
    try:
        (
            reservation,
            _entry,
            _token,
        ) = await waitlist_service.confirm_reservation_by_token(
            session,
            token_value=token,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if reservation.id != reservation_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Confirmation token does not match reservation",
        )
    return ReservationRead.model_validate(reservation)


@router.get(
    "/confirm/{token}",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    include_in_schema=False,
)
async def confirm_reservation_redirect(
    token: str,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
) -> RedirectResponse:
    success_url = (
        settings.portal_confirmation_success_url or "/portal/confirmation-success"
    )
    expired_url = (
        settings.portal_confirmation_expired_url or "/portal/confirmation-expired"
    )
    try:
        await waitlist_service.confirm_reservation_by_token(
            session,
            token_value=token,
        )
    except ValueError as exc:
        message = str(exc).lower()
        target = expired_url if "expired" in message else expired_url
        return RedirectResponse(
            url=target, status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    return RedirectResponse(
        url=success_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@router.delete(
    "/{reservation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete reservation",
)
async def delete_reservation(
    reservation_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> None:
    _assert_staff_authority(current_user)
    reservation = await reservation_service.get_reservation(
        session,
        account_id=current_user.account_id,
        reservation_id=reservation_id,
    )
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )
    try:
        await reservation_service.delete_reservation(
            session,
            reservation=reservation,
            account_id=current_user.account_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return None


@router.get(
    "/availability/daily",
    response_model=AvailabilityResponse,
    summary="Daily availability for a location",
)
async def get_daily_availability(
    params: Annotated[AvailabilityRequest, Depends()],
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> AvailabilityResponse:
    _assert_staff_authority(current_user)
    try:
        days = await reservation_service.get_daily_availability(
            session,
            account_id=current_user.account_id,
            location_id=params.location_id,
            reservation_type=params.reservation_type,
            start_date=params.start_date,
            end_date=params.end_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return AvailabilityResponse(
        location_id=params.location_id,
        reservation_type=params.reservation_type,
        days=[
            DailyAvailability.model_validate(day, from_attributes=True) for day in days
        ],
    )
