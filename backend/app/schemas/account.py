"""Account schemas for CRUD endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountBase(BaseModel):
    """Shared account fields."""

    name: str
    slug: str = Field(pattern=r"^[a-z0-9\-]+$")


class AccountCreate(AccountBase):
    """Payload for creating an account."""


class AccountUpdate(BaseModel):
    """Fields that can be updated on an account."""

    name: str | None = None
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9\-]+$")


class AccountRead(AccountBase):
    """Serialized account response."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
