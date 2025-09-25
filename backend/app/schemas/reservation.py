"""Pydantic schemas for reservations."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationStatus, ReservationType


class ReservationBase(BaseModel):
    """Shared reservation fields."""

    pet_id: uuid.UUID
    location_id: uuid.UUID
    reservation_type: ReservationType
    start_at: datetime
    end_at: datetime
    base_rate: Decimal = Field(gt=Decimal("0"))
    notes: str | None = None


class ReservationCreate(ReservationBase):
    """Payload for creating reservations."""

    status: ReservationStatus = ReservationStatus.REQUESTED


class ReservationUpdate(BaseModel):
    """Mutable reservation fields."""

    pet_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    reservation_type: ReservationType | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    base_rate: Decimal | None = Field(default=None, gt=Decimal("0"))
    status: ReservationStatus | None = None
    notes: str | None = None


class ReservationRead(ReservationBase):
    """Serialized reservation representation."""

    id: uuid.UUID
    account_id: uuid.UUID
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
