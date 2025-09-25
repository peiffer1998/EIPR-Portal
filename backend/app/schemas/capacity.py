"""Schemas for location capacity management."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationType


class CapacityRuleBase(BaseModel):
    """Shared fields for capacity rules."""

    reservation_type: ReservationType
    max_active: int | None = Field(default=None, ge=0)
    waitlist_limit: int | None = Field(default=None, ge=0)


class CapacityRuleCreate(CapacityRuleBase):
    """Payload to create a capacity rule for a location."""

    location_id: uuid.UUID


class CapacityRuleUpdate(BaseModel):
    """Mutable capacity rule fields."""

    max_active: int | None = Field(default=None, ge=0)
    waitlist_limit: int | None = Field(default=None, ge=0)


class CapacityRuleRead(CapacityRuleBase):
    """Serialized capacity rule response."""

    id: uuid.UUID
    location_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
