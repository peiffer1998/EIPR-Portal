"""Schemas for payment operations."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from app.models.payment import PaymentTransactionStatus


class PaymentIntentCreateRequest(BaseModel):
    """Request payload for creating or updating a payment intent."""

    invoice_id: UUID


class PaymentIntentCreateResponse(BaseModel):
    """Response payload returned when creating a payment intent."""

    client_secret: str
    transaction_id: UUID


class PaymentRefundRequest(BaseModel):
    """Request payload for issuing a refund."""

    invoice_id: UUID
    amount: Decimal | None = None


class PaymentRefundResponse(BaseModel):
    """Refund outcome response."""

    status: str
    amount: Decimal | None = None


class PaymentTransactionRead(BaseModel):
    id: UUID
    invoice_id: UUID
    owner_id: UUID
    provider: str
    amount: Decimal
    currency: str
    status: PaymentTransactionStatus
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
