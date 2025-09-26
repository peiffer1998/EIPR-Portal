"""Pydantic schemas for icon assignments."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.icon import IconEntity


class IconBase(BaseModel):
    """Shared icon fields."""

    name: str
    slug: str
    symbol: str | None = None
    color: str | None = None
    description: str | None = None
    applies_to: IconEntity = IconEntity.PET
    popup_text: str | None = None
    affects_capacity: bool = False


class IconCreate(IconBase):
    """Payload for creating an icon."""

    pass


class IconUpdate(BaseModel):
    """Mutable icon fields."""

    name: str | None = None
    slug: str | None = None
    symbol: str | None = None
    color: str | None = None
    description: str | None = None
    applies_to: IconEntity | None = None
    popup_text: str | None = None
    affects_capacity: bool | None = None


class IconRead(IconBase):
    """Serialized icon definition."""

    id: uuid.UUID
    account_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwnerIconAssignmentCreate(BaseModel):
    """Payload for attaching an icon to an owner."""

    owner_id: uuid.UUID
    icon_id: uuid.UUID
    notes: str | None = None


class OwnerIconAssignmentRead(BaseModel):
    """Icon assignment for an owner profile."""

    id: uuid.UUID
    icon: IconRead
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PetIconAssignmentCreate(BaseModel):
    """Payload for attaching an icon to a pet."""

    pet_id: uuid.UUID
    icon_id: uuid.UUID
    notes: str | None = None


class PetIconAssignmentRead(BaseModel):
    """Icon assignment for a pet profile."""

    id: uuid.UUID
    icon: IconRead
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
