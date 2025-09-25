"""Feeding schedule schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedingScheduleBase(BaseModel):
    """Shared feeding schedule fields."""

    scheduled_at: datetime
    food: str
    quantity: str | None = None
    notes: str | None = None


class FeedingScheduleCreate(FeedingScheduleBase):
    """Payload for creating a feeding schedule."""

    reservation_id: uuid.UUID


class FeedingScheduleUpdate(BaseModel):
    """Mutable feeding schedule fields."""

    scheduled_at: datetime | None = None
    food: str | None = None
    quantity: str | None = None
    notes: str | None = None


class FeedingScheduleRead(FeedingScheduleBase):
    """Serialized feeding schedule."""

    id: uuid.UUID
    reservation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
