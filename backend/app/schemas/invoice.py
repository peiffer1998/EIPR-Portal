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
    amount: Decimal = Field(gt=Decimal("0"))


class InvoiceItemCreate(InvoiceItemBase):
    """Payload to add an invoice item."""


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


class InvoicePromotionApply(BaseModel):
    """Payload to apply a promotion code."""

    code: str = Field(min_length=1)
