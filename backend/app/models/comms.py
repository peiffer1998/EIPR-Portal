"""Communication-related models (email, SMS, campaigns, notifications)."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models import Account, OwnerProfile, User


class EmailState(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class SMSDirection(str, enum.Enum):
    INBOUND = "in"
    OUTBOUND = "out"


class SMSStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RECEIVED = "received"


class CampaignChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class CampaignState(str, enum.Enum):
    DRAFT = "draft"
    SENDING = "sending"
    DONE = "done"
    FAILED = "failed"


class CampaignSendStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class NotificationType(str, enum.Enum):
    RESERVATION = "reservation"
    PAYMENT = "payment"
    MESSAGE = "message"
    SYSTEM = "system"


class EmailTemplate(TimestampMixin, Base):
    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_template: Mapped[str] = mapped_column(Text, nullable=False)
    html_template: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    account: Mapped["Account"] = relationship("Account")
    emails: Mapped[list["EmailOutbox"]] = relationship(
        "EmailOutbox", back_populates="template"
    )


class EmailOutbox(TimestampMixin, Base):
    __tablename__ = "emails_outbox"
    __table_args__ = (
        CheckConstraint("state in ('queued','sent','failed')", name="ck_email_state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    to_email: Mapped[str] = mapped_column(String(320), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    html: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[EmailState] = mapped_column(
        Enum(EmailState), default=EmailState.QUEUED, nullable=False
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account: Mapped["Account"] = relationship("Account")
    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile")
    template: Mapped[EmailTemplate | None] = relationship(
        "EmailTemplate", back_populates="emails"
    )


class SMSConversation(TimestampMixin, Base):
    __tablename__ = "sms_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    phone_e164: Mapped[str] = mapped_column(String(32), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account: Mapped["Account"] = relationship("Account")
    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile")
    messages: Mapped[list["SMSMessage"]] = relationship(
        "SMSMessage", back_populates="conversation", cascade="all, delete-orphan"
    )


class SMSMessage(Base):
    __tablename__ = "sms_messages"
    __table_args__ = (
        CheckConstraint("direction in ('in','out')", name="ck_sms_direction"),
        CheckConstraint(
            "status in ('queued','sent','delivered','failed','received')",
            name="ck_sms_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sms_conversations.id", ondelete="CASCADE"), nullable=False
    )
    direction: Mapped[SMSDirection] = mapped_column(Enum(SMSDirection), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SMSStatus] = mapped_column(Enum(SMSStatus), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    conversation: Mapped[SMSConversation] = relationship(
        "SMSConversation", back_populates="messages"
    )


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint("channel in ('email','sms')", name="ck_campaign_channel"),
        CheckConstraint(
            "state in ('draft','sending','done','failed')",
            name="ck_campaign_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[CampaignChannel] = mapped_column(
        Enum(CampaignChannel), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )
    segment: Mapped[dict] = mapped_column(JSON, nullable=False)
    state: Mapped[CampaignState] = mapped_column(
        Enum(CampaignState), default=CampaignState.DRAFT, nullable=False
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account: Mapped["Account"] = relationship("Account")
    template: Mapped[EmailTemplate | None] = relationship("EmailTemplate")
    sends: Mapped[list["CampaignSend"]] = relationship(
        "CampaignSend", back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignSend(TimestampMixin, Base):
    __tablename__ = "campaign_sends"
    __table_args__ = (
        CheckConstraint("channel in ('email','sms')", name="ck_campaign_send_channel"),
        CheckConstraint(
            "status in ('queued','sent','failed')",
            name="ck_campaign_send_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[CampaignChannel] = mapped_column(
        Enum(CampaignChannel), nullable=False
    )
    status: Mapped[CampaignSendStatus] = mapped_column(
        Enum(CampaignSendStatus), default=CampaignSendStatus.QUEUED, nullable=False
    )
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="sends")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type in ('reservation','payment','message','system')",
            name="ck_notification_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    account: Mapped["Account"] = relationship("Account")
    user: Mapped["User"] = relationship("User")
