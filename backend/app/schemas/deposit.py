"""Deposit lifecycle schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.deposit import DepositStatus


class DepositActionRequest(BaseModel):
    """Payload describing a deposit lifecycle action."""

    amount: Decimal = Field(gt=Decimal("0"))


class DepositRead(BaseModel):
    """Serialized deposit state."""

    id: uuid.UUID
    reservation_id: uuid.UUID
    owner_id: uuid.UUID
    amount: Decimal
    status: DepositStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
