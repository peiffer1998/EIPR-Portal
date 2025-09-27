"""Pydantic schemas for pet profiles."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.models.pet import PetType
from app.schemas.icon import PetIconAssignmentRead
from app.schemas.immunization import ImmunizationRecordRead


class OwnerSummary(BaseModel):
    """Lightweight owner representation for staff listings."""

    id: uuid.UUID
    first_name: str | None = Field(
        default=None, validation_alias=AliasPath("user", "first_name")
    )
    last_name: str | None = Field(
        default=None, validation_alias=AliasPath("user", "last_name")
    )
    email: str | None = Field(default=None, validation_alias=AliasPath("user", "email"))
    phone_number: str | None = Field(
        default=None, validation_alias=AliasPath("user", "phone_number")
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PetBase(BaseModel):
    """Shared pet fields."""

    owner_id: uuid.UUID
    home_location_id: uuid.UUID | None = None
    name: str
    pet_type: PetType
    breed: str | None = None
    color: str | None = None
    date_of_birth: date | None = None
    notes: str | None = None


class PetCreate(PetBase):
    """Payload for creating a pet."""

    pass


class PetUpdate(BaseModel):
    """Mutable pet fields."""

    owner_id: uuid.UUID | None = None
    home_location_id: uuid.UUID | None = None
    name: str | None = None
    pet_type: PetType | None = None
    breed: str | None = None
    color: str | None = None
    date_of_birth: date | None = None
    notes: str | None = None


class PetRead(PetBase):
    """Serialized pet representation."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    immunization_records: list[ImmunizationRecordRead] = Field(default_factory=list)
    icons: list[PetIconAssignmentRead] = Field(
        default_factory=list, alias="icon_assignments"
    )
    owner: OwnerSummary | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PetNoteCreate(BaseModel):
    """Payload for creating a pet note."""

    text: str = Field(min_length=1, max_length=2000)


class PetNoteRead(BaseModel):
    """Serialized pet note."""

    id: uuid.UUID
    pet_id: uuid.UUID
    text: str
    created_at: datetime
    author_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)
