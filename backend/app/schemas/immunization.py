"""Pydantic schemas for immunization management."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.immunization import ImmunizationStatus
from app.schemas.document import DocumentCreate, DocumentRead


class ImmunizationTypeBase(BaseModel):
    name: str
    description: str | None = Field(default=None, max_length=512)
    validity_days: int | None = Field(default=None, ge=0)
    reminder_days_before: int = Field(default=30, ge=0)
    is_required: bool = True


class ImmunizationTypeCreate(ImmunizationTypeBase):
    pass


class ImmunizationTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = Field(default=None, max_length=512)
    validity_days: int | None = Field(default=None, ge=0)
    reminder_days_before: int | None = Field(default=None, ge=0)
    is_required: bool | None = None


class ImmunizationTypeRead(ImmunizationTypeBase):
    id: uuid.UUID
    account_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImmunizationRecordBase(BaseModel):
    pet_id: uuid.UUID
    immunization_type_id: uuid.UUID
    received_on: date
    expires_on: date | None = None
    notes: str | None = Field(default=None, max_length=512)
    document_id: uuid.UUID | None = None
    document: DocumentCreate | None = None


class ImmunizationRecordCreate(ImmunizationRecordBase):
    pass


class ImmunizationRecordUpdate(BaseModel):
    received_on: date | None = None
    expires_on: date | None = None
    status: ImmunizationStatus | None = None
    notes: str | None = Field(default=None, max_length=512)
    document_id: uuid.UUID | None = None
    document: DocumentCreate | None = None


class ImmunizationRecordRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    pet_id: uuid.UUID
    immunization_type_id: uuid.UUID
    status: ImmunizationStatus
    received_on: date
    expires_on: date | None
    notes: str | None
    last_evaluated_at: datetime | None
    reminder_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
    immunization_type: ImmunizationTypeRead | None = None
    document: DocumentRead | None = None

    model_config = ConfigDict(from_attributes=True)
