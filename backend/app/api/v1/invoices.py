"""Invoice API endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.invoice import InvoiceStatus
from app.models.user import User, UserRole
from app.schemas.invoice import (
    InvoiceApplyPromotionRequest,
    InvoiceFromReservationRequest,
    InvoiceItemCreate,
    InvoiceListResponse,
    InvoicePaymentRequest,
    InvoiceRead,
    InvoiceSummaryRead,
    InvoiceTotalsRead,
)
from app.services import billing_service, invoice_service, notification_service

router = APIRouter(prefix="/invoices")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )


@router.get("", response_model=InvoiceListResponse, summary="List invoices")
async def list_invoices(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    status_filter: InvoiceStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, alias="q"),
) -> InvoiceListResponse:
    _assert_staff(current_user)

    start_dt: datetime | None = None
    end_dt: datetime | None = None
    if date_from is not None:
        start_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    if date_to is not None:
        end_dt = datetime.combine(date_to, time.max, tzinfo=timezone.utc)

    invoices, total = await billing_service.search_invoices(
        session,
        account_id=current_user.account_id,
        status=status_filter,
        date_from=start_dt,
        date_to=end_dt,
        query=search.strip() if search else None,
        limit=limit,
        offset=offset,
    )

    summaries: list[InvoiceSummaryRead] = []
    for inv in invoices:
        reservation = inv.reservation
        pet = getattr(reservation, "pet", None)
        owner = getattr(pet, "owner", None) if pet else None
        owner_user = getattr(owner, "user", None) if owner else None
        owner_name = None
        if owner_user is not None:
            owner_name = " ".join(
                filter(
                    None,
                    [owner_user.first_name, owner_user.last_name],
                )
            )
            owner_name = owner_name or owner_user.email

        summaries.append(
            InvoiceSummaryRead(
                id=inv.id,
                status=inv.status,
                total=inv.total,
                created_at=inv.created_at,
                reservation_id=inv.reservation_id,
                owner_id=owner.id if owner else None,
                owner_name=owner_name,
                pet_id=pet.id if pet else None,
                pet_name=pet.name if pet else None,
            )
        )

    return InvoiceListResponse(
        items=summaries,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{invoice_id}", response_model=InvoiceRead, summary="Get invoice")
async def get_invoice(
    invoice_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> InvoiceRead:
    _assert_staff(current_user)
    invoice = await billing_service.get_invoice(
        session, account_id=current_user.account_id, invoice_id=invoice_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    return InvoiceRead.model_validate(invoice)


@router.post(
    "/from-reservation",
    response_model=InvoiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an invoice from a reservation",
)
async def create_invoice_from_reservation(
    payload: InvoiceFromReservationRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
) -> InvoiceRead:
    _assert_staff(current_user)
    try:
        invoice_id = await invoice_service.create_from_reservation(
            session,
            reservation_id=payload.reservation_id,
            account_id=current_user.account_id,
            promotion_code=payload.promotion_code,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    invoice = await billing_service.get_invoice(
        session, account_id=current_user.account_id, invoice_id=invoice_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invoice not persisted",
        )
    notification_service.notify_invoice_available(invoice, background_tasks)
    return InvoiceRead.model_validate(invoice)


@router.post(
    "/{invoice_id}/items", response_model=InvoiceRead, summary="Add invoice item"
)
async def add_invoice_item(
    invoice_id: uuid.UUID,
    payload: InvoiceItemCreate,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
) -> InvoiceRead:
    _assert_staff(current_user)
    invoice = await billing_service.get_invoice(
        session, account_id=current_user.account_id, invoice_id=invoice_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    try:
        updated = await billing_service.add_invoice_item(
            session,
            invoice=invoice,
            account_id=current_user.account_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    notification_service.notify_invoice_available(updated, background_tasks)
    return InvoiceRead.model_validate(updated)


@router.post(
    "/{invoice_id}/apply-promo",
    response_model=InvoiceTotalsRead,
    summary="Apply promotion to invoice",
)
async def apply_invoice_promotion(
    invoice_id: uuid.UUID,
    payload: InvoiceApplyPromotionRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
) -> InvoiceTotalsRead:
    _assert_staff(current_user)
    try:
        totals = await invoice_service.compute_totals(
            session,
            invoice_id=invoice_id,
            account_id=current_user.account_id,
            promotion_code=payload.code,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return InvoiceTotalsRead.model_validate(totals)


@router.post(
    "/{invoice_id}/pay", response_model=InvoiceRead, summary="Process payment (mock)"
)
async def process_payment(
    invoice_id: uuid.UUID,
    payload: InvoicePaymentRequest,
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    background_tasks: BackgroundTasks,
) -> InvoiceRead:
    _assert_staff(current_user)
    invoice = await billing_service.get_invoice(
        session, account_id=current_user.account_id, invoice_id=invoice_id
    )
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )
    try:
        updated = await billing_service.process_payment(
            session,
            invoice=invoice,
            account_id=current_user.account_id,
            amount=payload.amount,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    notification_service.notify_payment_receipt(updated, background_tasks)
    return InvoiceRead.model_validate(updated)
