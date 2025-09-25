"""Pydantic schemas for pet profiles."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.pet import PetType


class PetBase(BaseModel):
    """Shared pet fields."""

    owner_id: uuid.UUID
    home_location_id: uuid.UUID | None = None
    name: str
    pet_type: PetType
    breed: str | None = None
    color: str | None = None
    date_of_birth: date | None = None
    notes: str | None = None


class PetCreate(PetBase):
    """Payload for creating a pet."""

    pass


class PetUpdate(BaseModel):
    """Mutable pet fields."""

    owner_id: uuid.UUID | None = None
    home_location_id: uuid.UUID | None = None
    name: str | None = None
    pet_type: PetType | None = None
    breed: str | None = None
    color: str | None = None
    date_of_birth: date | None = None
    notes: str | None = None


class PetRead(PetBase):
    """Serialized pet representation."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
