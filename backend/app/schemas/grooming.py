"""Pydantic schemas for grooming endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.grooming import CommissionType, GroomingAppointmentStatus


class SpecialistBase(BaseModel):
    name: str
    location_id: uuid.UUID
    user_id: uuid.UUID | None = None
    commission_type: CommissionType = CommissionType.PERCENT
    commission_rate: Decimal = Field(ge=Decimal("0"))
    active: bool = True


class SpecialistCreate(SpecialistBase):
    """Payload to create a specialist."""

    pass


class SpecialistUpdate(BaseModel):
    """Partial update to a specialist."""

    name: str | None = None
    user_id: uuid.UUID | None = None
    commission_type: CommissionType | None = None
    commission_rate: Decimal | None = Field(default=None, ge=Decimal("0"))
    active: bool | None = None


class SpecialistRead(SpecialistBase):
    """Serialized specialist."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroomingServiceBase(BaseModel):
    code: str
    name: str
    base_duration_minutes: int = Field(gt=0)
    base_price: Decimal = Field(gt=Decimal("0"))
    active: bool = True


class GroomingServiceCreate(GroomingServiceBase):
    """Create grooming service payload."""

    pass


class GroomingServiceUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    base_duration_minutes: int | None = Field(default=None, gt=0)
    base_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    active: bool | None = None


class GroomingServiceRead(GroomingServiceBase):
    id: uuid.UUID
    account_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroomingAddonBase(BaseModel):
    code: str
    name: str
    add_duration_minutes: int = Field(ge=0)
    add_price: Decimal = Field(ge=Decimal("0"))
    active: bool = True


class GroomingAddonCreate(GroomingAddonBase):
    pass


class GroomingAddonUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    add_duration_minutes: int | None = Field(default=None, ge=0)
    add_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    active: bool | None = None


class GroomingAddonRead(GroomingAddonBase):
    id: uuid.UUID
    account_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpecialistScheduleCreate(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time


class SpecialistScheduleRead(SpecialistScheduleCreate):
    id: uuid.UUID
    specialist_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpecialistTimeOffCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime
    reason: str | None = None


class SpecialistTimeOffRead(SpecialistTimeOffCreate):
    id: uuid.UUID
    specialist_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroomingAvailabilitySlot(BaseModel):
    start_at: datetime
    end_at: datetime
    specialist_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class GroomingAppointmentCreate(BaseModel):
    owner_id: uuid.UUID
    pet_id: uuid.UUID
    specialist_id: uuid.UUID
    service_id: uuid.UUID
    addon_ids: list[uuid.UUID] = Field(default_factory=list)
    start_at: datetime
    notes: str | None = None
    reservation_id: uuid.UUID | None = None


class GroomingAppointmentRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    owner_id: uuid.UUID
    pet_id: uuid.UUID
    specialist_id: uuid.UUID
    service_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    status: GroomingAppointmentStatus
    notes: str | None = None
    price_snapshot: Decimal | None = None
    commission_type: CommissionType | None = None
    commission_rate: Decimal | None = None
    commission_amount: Decimal | None = None
    invoice_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    addon_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroomingAppointmentListItem(GroomingAppointmentRead):
    service_name: str | None = None
    specialist_name: str | None = None


class GroomingAppointmentReschedule(BaseModel):
    new_start_at: datetime


class GroomingAppointmentStatusUpdate(BaseModel):
    new_status: GroomingAppointmentStatus


class GroomingAppointmentCancel(BaseModel):
    reason: str | None = None


class GroomingLoadSummary(BaseModel):
    date: date
    total_minutes: int
    status_counts: dict[str, int]


class GroomingCommissionSummary(BaseModel):
    specialist_id: uuid.UUID
    specialist_name: str | None = None
    total_commission: Decimal = Decimal("0")
    appointment_count: int
