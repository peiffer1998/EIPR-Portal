"""Pydantic schemas for owner profiles."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserRead


class OwnerBase(BaseModel):
    """Shared fields for owners."""

    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str | None = None
    preferred_contact_method: str | None = None
    notes: str | None = None
    is_primary_contact: bool = False


class OwnerCreate(OwnerBase):
    """Payload for creating an owner profile."""

    password: str = Field(min_length=8)


class OwnerUpdate(BaseModel):
    """Mutable owner fields."""

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    preferred_contact_method: str | None = None
    notes: str | None = None
    is_primary_contact: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class OwnerRead(BaseModel):
    """Serialized owner representation."""

    id: uuid.UUID
    preferred_contact_method: str | None
    notes: str | None
    user: UserRead
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
