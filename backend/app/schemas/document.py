"""Schemas for document uploads."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    file_name: str
    content_type: str | None = None
    url: str | None = None
    owner_id: uuid.UUID | None = None
    pet_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1024)


class DocumentRead(DocumentCreate):
    id: uuid.UUID
    account_id: uuid.UUID
    uploaded_by_user_id: uuid.UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
