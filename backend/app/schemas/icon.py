"""Schemas for icon definitions and assignments."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.icon import IconEntity


class IconCreate(BaseModel):
    name: str
    slug: str = Field(min_length=1, max_length=120)
    symbol: str | None = Field(default=None, max_length=16)
    color: str | None = Field(default=None, max_length=16)
    description: str | None = None
    applies_to: IconEntity = IconEntity.PET
    popup_text: str | None = Field(default=None, max_length=512)
    affects_capacity: bool = False


class IconUpdate(BaseModel):
    name: str | None = None
    slug: str | None = Field(default=None, max_length=120)
    symbol: str | None = Field(default=None, max_length=16)
    color: str | None = Field(default=None, max_length=16)
    description: str | None = None
    applies_to: IconEntity | None = None
    popup_text: str | None = Field(default=None, max_length=512)
    affects_capacity: bool | None = None


class IconRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    name: str
    slug: str
    symbol: str | None
    color: str | None
    description: str | None
    applies_to: IconEntity
    popup_text: str | None
    affects_capacity: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwnerIconAssignmentCreate(BaseModel):
    owner_id: uuid.UUID
    icon_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=512)


class OwnerIconAssignmentRead(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    icon: IconRead
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PetIconAssignmentCreate(BaseModel):
    pet_id: uuid.UUID
    icon_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=512)


class PetIconAssignmentRead(BaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    icon: IconRead
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
