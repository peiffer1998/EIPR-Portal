"""Schemas for location hours and closures."""

from __future__ import annotations

import uuid
from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field


class LocationHourCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    open_time: time | None = None
    close_time: time | None = None
    is_closed: bool = False


class LocationHourUpdate(BaseModel):
    open_time: time | None = None
    close_time: time | None = None
    is_closed: bool | None = None


class LocationHourRead(LocationHourCreate):
    id: uuid.UUID
    location_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class LocationClosureCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str | None = Field(default=None, max_length=255)


class LocationClosureRead(LocationClosureCreate):
    id: uuid.UUID
    location_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
