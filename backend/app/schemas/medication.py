"""Medication schedule schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MedicationScheduleBase(BaseModel):
    """Shared medication schedule fields."""

    scheduled_at: datetime
    medication: str
    dosage: str | None = None
    notes: str | None = None


class MedicationScheduleCreate(MedicationScheduleBase):
    """Payload for creating a medication schedule."""

    reservation_id: uuid.UUID


class MedicationScheduleUpdate(BaseModel):
    """Mutable medication schedule fields."""

    scheduled_at: datetime | None = None
    medication: str | None = None
    dosage: str | None = None
    notes: str | None = None


class MedicationScheduleRead(MedicationScheduleBase):
    """Serialized medication schedule."""

    id: uuid.UUID
    reservation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
