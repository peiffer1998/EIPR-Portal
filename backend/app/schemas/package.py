"""Schemas for service packages."""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationType


class ServicePackageBase(BaseModel):
    name: str
    description: str | None = None
    reservation_type: ReservationType
    credit_quantity: int = Field(ge=1)
    price: Decimal = Field(ge=0)
    active: bool = True


class ServicePackageCreate(ServicePackageBase):
    pass


class ServicePackageUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    credit_quantity: int | None = Field(default=None, ge=1)
    price: Decimal | None = Field(default=None, ge=0)
    active: bool | None = None


class ServicePackageRead(ServicePackageBase):
    id: uuid.UUID
    account_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
