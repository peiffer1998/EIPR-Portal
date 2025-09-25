"""User-related schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole, UserStatus


class UserBase(BaseModel):
    """Shared user fields."""

    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str | None = None
    role: UserRole = Field(default=UserRole.STAFF)


class UserCreate(UserBase):
    """Payload for creating a user."""

    password: str = Field(min_length=8)
    account_id: uuid.UUID
    status: UserStatus = UserStatus.ACTIVE
    is_primary_contact: bool = False


class UserRead(UserBase):
    """Serialized user response."""

    id: uuid.UUID
    account_id: uuid.UUID
    status: UserStatus
    is_primary_contact: bool

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Mutable user fields."""

    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
    is_primary_contact: bool | None = None
