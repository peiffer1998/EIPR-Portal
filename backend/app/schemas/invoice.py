"""Invoice schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.invoice import InvoiceStatus


class InvoiceItemBase(BaseModel):
    """Shared fields for invoice items."""

    description: str
    amount: Decimal


class InvoiceItemCreate(InvoiceItemBase):
    """Payload to add an invoice item."""

    amount: Decimal = Field(gt=Decimal("0"))


class InvoiceItemRead(InvoiceItemBase):
    """Serialized invoice item."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceRead(BaseModel):
    """Serialized invoice."""

    id: uuid.UUID
    account_id: uuid.UUID
    reservation_id: uuid.UUID
    status: InvoiceStatus
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    credits_total: Decimal
    total_amount: Decimal
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InvoicePaymentRequest(BaseModel):
    """Mock payment processing payload."""

    amount: Decimal = Field(gt=Decimal("0"))
    note: str | None = None


class InvoiceFromReservationRequest(BaseModel):
    """Request payload to generate an invoice from a reservation."""

    reservation_id: uuid.UUID
    promotion_code: str | None = None


class InvoiceApplyPromotionRequest(BaseModel):
    """Request payload to recalculate totals with a promotion."""

    code: str


class InvoiceTotalsRead(BaseModel):
    """Expose invoice totals after recalculation."""

    invoice_id: uuid.UUID
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    credits_total: Decimal
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class InvoiceSummaryRead(BaseModel):
    """Lightweight representation for invoice listing."""

    id: uuid.UUID
    status: InvoiceStatus
    total: Decimal
    created_at: datetime
    reservation_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    owner_name: str | None = None
    pet_id: uuid.UUID | None = None
    pet_name: str | None = None


class InvoiceListResponse(BaseModel):
    """Paginated invoice listing payload."""

    items: list[InvoiceSummaryRead]
    total: int
    limit: int
    offset: int
