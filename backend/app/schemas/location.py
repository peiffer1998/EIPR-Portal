"""Location schemas for CRUD operations."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocationBase(BaseModel):
    """Shared location fields."""

    account_id: uuid.UUID
    name: str
    timezone: str
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    phone_number: str | None = Field(default=None, max_length=32)


class LocationCreate(LocationBase):
    """Payload for creating a location."""


class LocationUpdate(BaseModel):
    """Mutable location fields."""

    name: str | None = None
    timezone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    phone_number: str | None = Field(default=None, max_length=32)


class LocationRead(LocationBase):
    """Serialized location response."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
