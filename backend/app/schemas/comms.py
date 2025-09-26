"""Schemas for communications (email, SMS, campaigns, notifications)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.comms import (
    CampaignChannel,
    CampaignSendStatus,
    EmailState,
    NotificationType,
    SMSDirection,
    SMSStatus,
)


class EmailTemplateBase(BaseModel):
    name: str
    subject_template: str
    html_template: str
    active: bool = True


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    subject_template: str | None = None
    html_template: str | None = None
    active: bool | None = None


class EmailTemplateRead(EmailTemplateBase):
    id: UUID
    account_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmailSendRequest(BaseModel):
    owner_id: UUID
    template_name: str | None = None
    subject: str | None = None
    html: str | None = None
    context: dict[str, Any] | None = None


class EmailSendResponse(BaseModel):
    outbox_id: UUID
    state: EmailState


class SMSSendRequest(BaseModel):
    owner_id: UUID
    body: str = Field(min_length=1, max_length=1000)


class SMSConversationRead(BaseModel):
    id: UUID
    phone_e164: str
    last_message_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SMSMessageRead(BaseModel):
    id: UUID
    direction: SMSDirection
    status: SMSStatus
    body: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignPreviewRequest(BaseModel):
    channel: CampaignChannel
    segment: dict[str, Any] | None = None


class CampaignPreviewResponse(BaseModel):
    count: int


class CampaignSendNowRequest(CampaignPreviewRequest):
    template_name: str


class CampaignSendRead(BaseModel):
    id: UUID
    owner_id: UUID
    status: CampaignSendStatus
    created_at: datetime
    sent_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationRead(BaseModel):
    id: UUID
    type: NotificationType
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    notifications: list[NotificationRead]


class NotificationMarkReadResponse(BaseModel):
    id: UUID
    read_at: datetime
