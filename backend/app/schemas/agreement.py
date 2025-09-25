"""Schemas for agreement templates and signatures."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgreementTemplateCreate(BaseModel):
    title: str
    body: str
    requires_signature: bool = True
    is_active: bool = True
    version: int = Field(default=1, ge=1)


class AgreementTemplateUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    requires_signature: bool | None = None
    is_active: bool | None = None
    version: int | None = Field(default=None, ge=1)


class AgreementTemplateRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    title: str
    body: str
    requires_signature: bool
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgreementSignatureCreate(BaseModel):
    agreement_template_id: uuid.UUID
    owner_id: uuid.UUID | None = None
    pet_id: uuid.UUID | None = None
    signed_by_user_id: uuid.UUID | None = None
    ip_address: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=512)


class AgreementSignatureRead(BaseModel):
    id: uuid.UUID
    agreement_template_id: uuid.UUID
    owner_id: uuid.UUID | None
    pet_id: uuid.UUID | None
    signed_by_user_id: uuid.UUID | None
    signed_at: datetime
    ip_address: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
