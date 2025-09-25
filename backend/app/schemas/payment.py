"""Payment schemas."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentIntentCreate(BaseModel):
    """Request payload to create a payment intent."""

    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=Decimal("0"))


class PaymentIntentConfirm(BaseModel):
    """Request payload to confirm a payment intent."""

    payment_intent_id: str = Field(min_length=1)


class PaymentIntentRead(BaseModel):
    """Serialized payment intent response."""

    payment_intent_id: str
    client_secret: str | None = None
    status: str
    invoice_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class WebhookAck(BaseModel):
    """Webhook acknowledgement."""

    received: bool = True
