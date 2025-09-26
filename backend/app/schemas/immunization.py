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
    validity_days: int | None = Field(default=None, ge=0, alias="default_valid_days")
    reminder_days_before: int = Field(default=30, ge=0)
    is_required: bool = Field(default=True, alias="required")

    model_config = ConfigDict(populate_by_name=True)


class ImmunizationTypeCreate(ImmunizationTypeBase):
    pass


class ImmunizationTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = Field(default=None, max_length=512)
    validity_days: int | None = Field(default=None, ge=0)
    reminder_days_before: int | None = Field(default=None, ge=0)
    is_required: bool | None = Field(default=None, alias="required")

    model_config = ConfigDict(populate_by_name=True)


class ImmunizationTypeRead(ImmunizationTypeBase):
    id: uuid.UUID
    account_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImmunizationRecordBase(BaseModel):
    pet_id: uuid.UUID | None = None
    type_id: uuid.UUID = Field(alias="immunization_type_id")
    issued_on: date
    expires_on: date | None = None
    verified: bool = False
    notes: str | None = Field(default=None, max_length=512)
    document_id: uuid.UUID | None = None
    document: DocumentCreate | None = None

    model_config = ConfigDict(populate_by_name=True)


class ImmunizationRecordCreate(ImmunizationRecordBase):
    pass


class ImmunizationRecordUpdate(BaseModel):
    issued_on: date | None = None
    expires_on: date | None = None
    status: ImmunizationStatus | None = None
    notes: str | None = Field(default=None, max_length=512)
    document_id: uuid.UUID | None = None
    document: DocumentCreate | None = None
    verified: bool | None = None


class ImmunizationRecordRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    pet_id: uuid.UUID
    immunization_type_id: uuid.UUID = Field(alias="type_id")
    status: ImmunizationStatus
    issued_on: date
    expires_on: date | None
    notes: str | None
    last_evaluated_at: datetime | None = None
    reminder_sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    immunization_type: ImmunizationTypeRead | None = None
    document: DocumentRead | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ImmunizationRecordStatus(BaseModel):
    """Rendered status view for an immunization record."""

    record: ImmunizationRecordRead
    is_pending: bool
    is_current: bool
    is_expiring: bool
    is_expired: bool
    is_required: bool

    model_config = ConfigDict(from_attributes=True)
