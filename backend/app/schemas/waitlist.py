"""Schemas for waitlist entries."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationType
from app.models.waitlist_entry import WaitlistStatus


class WaitlistEntryCreate(BaseModel):
    pet_id: uuid.UUID
    location_id: uuid.UUID
    reservation_type: ReservationType
    desired_date: date
    notes: str | None = Field(default=None, max_length=1024)


class WaitlistEntryRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    pet_id: uuid.UUID
    location_id: uuid.UUID
    reservation_type: ReservationType
    desired_date: date
    status: WaitlistStatus
    notes: str | None = None
    offered_at: datetime | None = None
    confirmed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WaitlistStatusUpdate(BaseModel):
    status: WaitlistStatus
