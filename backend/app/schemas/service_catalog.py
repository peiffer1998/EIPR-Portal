"""Schemas for service catalog items."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationType
from app.models.service_catalog_item import ServiceCatalogKind


class ServiceCatalogItemBase(BaseModel):
    name: str
    description: str | None = None
    kind: ServiceCatalogKind = ServiceCatalogKind.SERVICE
    reservation_type: ReservationType | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    base_price: Decimal | None = Field(default=None, ge=0)
    active: bool = True
    sku: str | None = None


class ServiceCatalogItemCreate(ServiceCatalogItemBase):
    pass


class ServiceCatalogItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    reservation_type: ReservationType | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    base_price: Decimal | None = Field(default=None, ge=0)
    active: bool | None = None
    sku: str | None = None


class ServiceCatalogItemRead(ServiceCatalogItemBase):
    id: uuid.UUID
    account_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
