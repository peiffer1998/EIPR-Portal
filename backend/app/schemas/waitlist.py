"""Schemas for waitlist entries and offers."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.waitlist_entry import (
    WaitlistEntry,
    WaitlistServiceType,
    WaitlistStatus,
)


class WaitlistPetPayload(BaseModel):
    pet_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=512)
    reservation_id: uuid.UUID | None = None


class WaitlistEntryCreate(BaseModel):
    location_id: uuid.UUID
    owner_id: uuid.UUID
    service_type: WaitlistServiceType
    lodging_type_id: uuid.UUID | None = None
    start_date: date
    end_date: date
    pets: list[WaitlistPetPayload]
    notes: str | None = Field(default=None, max_length=1024)
    priority: int | None = None


class WaitlistEntryRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    location_id: uuid.UUID
    owner_id: uuid.UUID
    service_type: WaitlistServiceType
    lodging_type_id: uuid.UUID | None = None
    start_date: date
    end_date: date
    pets: list[WaitlistPetPayload]
    notes: str | None = None
    status: WaitlistStatus
    priority: int
    offered_at: datetime | None = None
    expires_at: datetime | None = None
    converted_reservation_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_entry(cls, entry: WaitlistEntry) -> "WaitlistEntryRead":
        return cls.model_validate(
            {
                "id": entry.id,
                "account_id": entry.account_id,
                "location_id": entry.location_id,
                "owner_id": entry.owner_id,
                "service_type": entry.service_type,
                "lodging_type_id": entry.lodging_type_id,
                "start_date": entry.start_date,
                "end_date": entry.end_date,
                "pets": entry.pets_json,
                "notes": entry.notes,
                "status": entry.status,
                "priority": entry.priority,
                "offered_at": entry.offered_at,
                "expires_at": entry.expires_at,
                "converted_reservation_id": entry.converted_reservation_id,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
            }
        )


class WaitlistEntryUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=1024)
    priority: int | None = None
    status: Literal[WaitlistStatus.CANCELED] | None = None


class WaitlistOfferRequest(BaseModel):
    hold_minutes: int = Field(default=240, ge=5, le=2880)
    lodging_type_id: uuid.UUID | None = None
    method: Literal["email", "sms"] = "email"
    sent_to: str | None = Field(default=None, max_length=320)


class WaitlistOfferResponse(BaseModel):
    reservation_ids: list[uuid.UUID]
    token: str
    expires_at: datetime


class WaitlistPromoteRequest(BaseModel):
    lodging_type_id: uuid.UUID | None = None


class WaitlistListResponse(BaseModel):
    entries: list[WaitlistEntryRead]
    next_cursor: str | None = None
