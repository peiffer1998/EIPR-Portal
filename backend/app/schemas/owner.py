"""Pydantic schemas for owner profiles."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.user import _validate_relaxed_email

from app.models.reservation import ReservationType
from app.schemas.user import UserRead
from app.schemas.icon import OwnerIconAssignmentRead


class OwnerBase(BaseModel):
    """Shared fields for owners."""

    first_name: str
    last_name: str
    email: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        return _validate_relaxed_email(value)

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
    icons: list[OwnerIconAssignmentRead] = Field(
        default_factory=list, alias="icon_assignments"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OwnerNoteCreate(BaseModel):
    """Payload for creating an owner note."""

    text: str = Field(min_length=1, max_length=2000)


class OwnerNoteRead(BaseModel):
    """Serialized owner note."""

    id: uuid.UUID
    owner_id: uuid.UUID
    text: str
    created_at: datetime
    author_id: uuid.UUID | None = None


class OwnerReservationRequest(BaseModel):
    """Owner-initiated reservation payload."""

    pet_id: uuid.UUID
    location_id: uuid.UUID
    reservation_type: ReservationType
    start_at: datetime
    end_at: datetime
    notes: str | None = None
