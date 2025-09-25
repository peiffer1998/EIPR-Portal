"""User-related schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.staff_invitation import StaffInvitationStatus
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


class StaffInvitationCreate(BaseModel):
    """Payload to invite a staff member."""

    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    phone_number: str | None = None
    expires_in_hours: int = Field(default=72, ge=1, le=240)


class StaffInvitationRead(BaseModel):
    """Serialized staff invitation."""

    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str | None = None
    role: UserRole
    status: StaffInvitationStatus
    expires_at: datetime
    created_at: datetime
    accepted_at: datetime | None = None
    invite_token: str | None = None

    model_config = ConfigDict(from_attributes=True)
