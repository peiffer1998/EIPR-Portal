"""Schemas for document uploads."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    file_name: str
    content_type: str | None = None
    object_key: str | None = None
    url: str | None = None
    owner_id: uuid.UUID | None = None
    pet_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1024)
    sha256: str | None = Field(default=None, max_length=128)
    object_key_web: str | None = Field(default=None, max_length=1024)
    bytes_web: int | None = None
    width: int | None = None
    height: int | None = None
    content_type_web: str | None = Field(default=None, max_length=128)
    url_web: str | None = None


class DocumentRead(DocumentCreate):
    id: uuid.UUID
    account_id: uuid.UUID
    uploaded_by_user_id: uuid.UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentFinalizeRequest(BaseModel):
    upload_key: str
    file_name: str
    content_type: str
    owner_id: uuid.UUID | None = None
    pet_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1024)
    url: str | None = None
