"""Authentication schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.owner import OwnerRead


class Token(BaseModel):
    """Response body for access tokens."""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str


class RegistrationRequest(BaseModel):
    """Self-service registration payload for pet parents."""

    account_slug: str = Field(min_length=3)
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    last_name: str
    phone_number: str | None = None
    preferred_contact_method: str | None = None
    notes: str | None = None


class RegistrationResponse(BaseModel):
    """Response after successful self-service registration."""

    token: Token
    owner: OwnerRead


class PasswordResetRequest(BaseModel):
    """Request body to initiate a password reset."""

    email: EmailStr


class PasswordResetTokenResponse(BaseModel):
    """Password reset initiation response."""

    reset_token: str | None = None
    expires_at: datetime | None = None


class PasswordResetConfirm(BaseModel):
    """Payload to finalize a password reset."""

    token: str
    new_password: str = Field(min_length=8)
