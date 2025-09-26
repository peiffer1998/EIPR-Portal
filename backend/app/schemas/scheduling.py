"""Scheduling-related schemas."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.reservation import ReservationType


class DailyAvailability(BaseModel):
    """Availability summary for a single day."""

    date: date
    capacity: int | None
    booked: int
    available: int | None


class AvailabilityRequest(BaseModel):
    """Availability request parameters."""

    location_id: uuid.UUID
    reservation_type: ReservationType
    start_date: date
    end_date: date


class AvailabilityResponse(BaseModel):
    """Availability response payload."""

    location_id: uuid.UUID
    reservation_type: ReservationType
    days: list[DailyAvailability]

    model_config = ConfigDict(from_attributes=True)
