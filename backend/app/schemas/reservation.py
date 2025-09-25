"""Pydantic schemas for reservations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationStatus, ReservationType
from app.schemas.feeding import FeedingScheduleRead
from app.schemas.medication import MedicationScheduleRead


class ReservationBase(BaseModel):
    """Shared reservation fields."""

    pet_id: uuid.UUID
    location_id: uuid.UUID
    reservation_type: ReservationType
    start_at: datetime
    end_at: datetime
    base_rate: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    notes: str | None = None
    kennel_id: uuid.UUID | None = None


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
    base_rate: Decimal | None = Field(default=None, ge=Decimal("0"))
    status: ReservationStatus | None = None
    notes: str | None = None
    kennel_id: uuid.UUID | None = None


class ReservationRead(ReservationBase):
    """Serialized reservation representation."""

    id: uuid.UUID
    account_id: uuid.UUID
    status: ReservationStatus
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    feeding_schedules: list[FeedingScheduleRead] = Field(default_factory=list)
    medication_schedules: list[MedicationScheduleRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ReservationCheckInRequest(BaseModel):
    """Payload for reservation check-in."""

    check_in_at: datetime | None = None
    kennel_id: uuid.UUID | None = None

    def resolve_timestamp(self) -> datetime:
        ts = self.check_in_at or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)


class ReservationCheckOutRequest(BaseModel):
    """Payload for reservation check-out."""

    check_out_at: datetime | None = None

    def resolve_timestamp(self) -> datetime:
        ts = self.check_out_at or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
