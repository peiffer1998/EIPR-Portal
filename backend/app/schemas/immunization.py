"""Pydantic schemas for health track immunizations."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.immunization import ImmunizationStatus


class ImmunizationTypeBase(BaseModel):
    name: str = Field(max_length=120)
    required: bool = Field(default=False)
    default_valid_days: int | None = Field(default=None, ge=0)


class ImmunizationTypeCreate(ImmunizationTypeBase):
    pass


class ImmunizationTypeRead(ImmunizationTypeBase):
    id: uuid.UUID
    account_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImmunizationRecordCreate(BaseModel):
    type_id: uuid.UUID
    issued_on: date
    expires_on: date | None = None
    notes: str | None = Field(default=None, max_length=1024)
    verified: bool = False


class ImmunizationRecordRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    pet_id: uuid.UUID
    type_id: uuid.UUID
    status: ImmunizationStatus
    issued_on: date
    expires_on: date | None
    verified_by_user_id: uuid.UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    immunization_type: ImmunizationTypeRead | None = None

    model_config = ConfigDict(from_attributes=True)


class ImmunizationRecordStatus(BaseModel):
    record: ImmunizationRecordRead
    is_pending: bool
    is_current: bool
    is_expiring: bool
    is_expired: bool
    is_required: bool

    model_config = ConfigDict(from_attributes=True)
