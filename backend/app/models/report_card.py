"""Report card domain models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Integer,
    Column,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only imports
    from app.models import Account, Document, OwnerProfile, Pet, Reservation, User


class ReportCardStatus(str, enum.Enum):
    """Lifecycle of a report card."""

    DRAFT = "draft"
    SENT = "sent"


class ReportCard(TimestampMixin, Base):
    """Summary of a pet's stay including media and notes."""

    __tablename__ = "report_cards"
    __table_args__ = (
        Index("ix_report_cards_pet_id", "pet_id"),
        Index("ix_report_cards_occurred_on", "occurred_on"),
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
    pet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True
    )
    occurred_on: Mapped[date] = mapped_column(Date(), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text())
    rating: Mapped[int | None] = mapped_column(SmallInteger())
    status: Mapped[ReportCardStatus] = mapped_column(
        Enum(
            ReportCardStatus,
            name="reportcardstatus",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ReportCardStatus.DRAFT,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    account: Mapped["Account"] = relationship("Account")
    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile")
    pet: Mapped["Pet"] = relationship("Pet")
    reservation: Mapped["Reservation | None"] = relationship("Reservation")
    created_by: Mapped["User"] = relationship("User")
    media: Mapped[list["ReportCardMedia"]] = relationship(
        "ReportCardMedia",
        back_populates="report_card",
        cascade="all, delete-orphan",
        order_by="ReportCardMedia.position",
    )
    friends: Mapped[list["Pet"]] = relationship(
        "Pet",
        secondary="report_card_friends",
        lazy="selectin",
    )


class ReportCardMedia(TimestampMixin, Base):
    """Association between report card and media documents."""

    __tablename__ = "report_card_media"
    __table_args__ = (
        Index("ix_report_card_media_card_position", "report_card_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    report_card_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("report_cards.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    report_card: Mapped["ReportCard"] = relationship(
        "ReportCard", back_populates="media"
    )
    document: Mapped["Document"] = relationship("Document")


report_card_friends = Table(
    "report_card_friends",
    Base.metadata,
    Column(
        "report_card_id",
        ForeignKey("report_cards.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "friend_pet_id",
        ForeignKey("pets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    UniqueConstraint("report_card_id", "friend_pet_id", name="uq_report_card_friend"),
)
