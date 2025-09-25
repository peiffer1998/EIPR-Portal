"""Schemas supporting OPS P5 operations features."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationType


class FeedingBoardItem(BaseModel):
    """Single feeding schedule entry."""

    model_config = ConfigDict(from_attributes=True)

    scheduled_at: datetime
    food: str
    quantity: str | None = None
    notes: str | None = None


class FeedingBoardRow(BaseModel):
    """Aggregated feeding view per reservation."""

    model_config = ConfigDict(from_attributes=True)

    reservation_id: UUID
    pet_name: str
    owner_name: str
    reservation_type: ReservationType
    start_at: datetime
    end_at: datetime
    reservation_notes: str | None = None
    schedule_items: list[FeedingBoardItem] = Field(default_factory=list)


class MedicationBoardItem(BaseModel):
    """Single medication schedule entry."""

    model_config = ConfigDict(from_attributes=True)

    scheduled_at: datetime
    medication: str
    dosage: str | None = None
    notes: str | None = None


class MedicationBoardRow(BaseModel):
    """Aggregated medication view per reservation."""

    model_config = ConfigDict(from_attributes=True)

    reservation_id: UUID
    pet_name: str
    owner_name: str
    reservation_type: ReservationType
    start_at: datetime
    end_at: datetime
    reservation_notes: str | None = None
    schedule_items: list[MedicationBoardItem] = Field(default_factory=list)


class RunCardContext(BaseModel):
    """Data rendered into printable run cards."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    location_name: str
    feedings: list[FeedingBoardRow]
    medications: list[MedicationBoardRow]
