"""Schemas for report cards."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.models.report_card import ReportCardStatus
from app.models.pet import PetType
from app.schemas.document import DocumentRead


class ReportCardCreate(BaseModel):
    owner_id: uuid.UUID
    pet_id: uuid.UUID
    occurred_on: date
    created_by_user_id: uuid.UUID
    reservation_id: uuid.UUID | None = None
    title: str | None = None
    summary: str | None = None
    rating: int | None = Field(default=None, ge=0, le=5)


class ReportCardUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    rating: int | None = Field(default=None, ge=0, le=5)
    occurred_on: date | None = None
    reservation_id: uuid.UUID | None = None


class ReportCardMediaAttach(BaseModel):
    document_ids: Sequence[uuid.UUID] = Field(default_factory=list)


class ReportCardFriendsUpdate(BaseModel):
    friend_pet_ids: Sequence[uuid.UUID] = Field(default_factory=list)


class ReportCardFriendRead(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    pet_type: PetType

    model_config = ConfigDict(from_attributes=True)


class ReportCardMediaRead(BaseModel):
    id: uuid.UUID
    report_card_id: uuid.UUID
    position: int
    document: DocumentRead
    display_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReportCardRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    owner_id: uuid.UUID
    pet_id: uuid.UUID
    reservation_id: uuid.UUID | None = None
    occurred_on: date
    title: str | None = None
    summary: str | None = None
    rating: int | None = None
    status: ReportCardStatus
    created_by_user_id: uuid.UUID
    sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    media: list[ReportCardMediaRead] = Field(default_factory=list)
    friends: list[ReportCardFriendRead] = Field(default_factory=list)
    pet_name: str | None = None
    owner_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
