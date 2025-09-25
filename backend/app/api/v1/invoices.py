"""Invoice API endpoints."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.invoice import InvoiceStatus
from app.models.user import User, UserRole
from app.schemas.invoice import InvoiceItemCreate, InvoicePaymentRequest, InvoiceRead
from app.services import billing_service, notification_service

router = APIRouter(prefix="/invoices")


def _assert_staff(user: User) -> None:
    if user.role == UserRole.PET_PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("", response_model=list[InvoiceRead], summary="List invoices")
async def list_invoices(
    session: Annotated[AsyncSession, Depends(deps.get_db_session)],
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    status_filter: InvoiceStatus | None = Query(default=None, alias="status"),
) -> list[InvoiceRead]:
    _assert_staff(current_user)
    invoices = await billing_service.list_invoices(
        session, account_id=current_user.account_id, status=status_filter
    )
    return [InvoiceRead.model_validate(inv) for inv in invoices]


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return InvoiceRead.model_validate(invoice)


@router.post("/{invoice_id}/items", response_model=InvoiceRead, summary="Add invoice item")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    try:
        updated = await billing_service.add_invoice_item(
            session, invoice=invoice, account_id=current_user.account_id, payload=payload
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    notification_service.notify_invoice_available(updated, background_tasks)
    return InvoiceRead.model_validate(updated)


@router.post("/{invoice_id}/pay", response_model=InvoiceRead, summary="Process payment (mock)")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    try:
        updated = await billing_service.process_payment(
            session,
            invoice=invoice,
            account_id=current_user.account_id,
            amount=payload.amount,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    notification_service.notify_payment_receipt(updated, background_tasks)
    return InvoiceRead.model_validate(updated)
