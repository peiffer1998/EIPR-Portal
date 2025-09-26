"""Schemas for payroll domain."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payroll import TipPolicy


class TimeClockPunchRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    location_id: uuid.UUID
    user_id: uuid.UUID
    clock_in_at: datetime
    clock_out_at: datetime | None = None
    rounded_in_at: datetime
    rounded_out_at: datetime | None = None
    minutes_worked: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TipShareRead(BaseModel):
    user_id: uuid.UUID
    amount: Decimal = Field(ge=Decimal("0"))
    method: str


class TipCreate(BaseModel):
    location_id: uuid.UUID
    date: date
    amount: Decimal = Field(ge=Decimal("0"))
    policy: TipPolicy
    appointment_id: uuid.UUID | None = None
    payment_transaction_id: uuid.UUID | None = None
    recipients: list[tuple[uuid.UUID, Decimal]] | None = None
    note: str | None = None


class TipRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    location_id: uuid.UUID
    date: date
    amount: Decimal
    policy: TipPolicy
    shares: list[TipShareRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommissionPayoutRead(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    specialist_id: uuid.UUID
    basis_amount: Decimal | None = None
    commission_amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayrollPeriodCreate(BaseModel):
    location_id: uuid.UUID | None = None
    starts_on: date
    ends_on: date


class PayrollPeriodRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    location_id: uuid.UUID | None
    starts_on: date
    ends_on: date
    locked_at: datetime | None = None
    paid_at: datetime | None = None
    totals: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
