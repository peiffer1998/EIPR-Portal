"""Immunization-related models for pet health tracking."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models import Document, Pet


class ImmunizationStatus(str, enum.Enum):
    """Current validity state for an immunization record."""

    VALID = "valid"
    EXPIRING = "expiring"
    EXPIRED = "expired"


class ImmunizationType(TimestampMixin, Base):
    """Configurable immunization rules per account."""

    __tablename__ = "immunization_types"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512))
    validity_days: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    reminder_days_before: Mapped[int] = mapped_column(
        Integer(), nullable=False, default=30
    )
    is_required: Mapped[bool] = mapped_column(default=True)

    records: Mapped[list["ImmunizationRecord"]] = relationship(
        "ImmunizationRecord",
        back_populates="immunization_type",
        cascade="all, delete-orphan",
    )


class ImmunizationRecord(TimestampMixin, Base):
    """Recorded immunization for a specific pet."""

    __tablename__ = "immunization_records"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "pet_id",
            "immunization_type_id",
            "received_on",
            name="uq_immunization_per_visit",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    immunization_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("immunization_types.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    expires_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ImmunizationStatus] = mapped_column(
        Enum(ImmunizationStatus), default=ImmunizationStatus.VALID, nullable=False
    )
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(String(512))

    immunization_type: Mapped[ImmunizationType] = relationship(
        "ImmunizationType", back_populates="records"
    )
    pet: Mapped["Pet"] = relationship("Pet", back_populates="immunization_records")
    document: Mapped["Document | None"] = relationship("Document")

    @property
    def is_expired(self) -> bool:
        """Return True if the record is past its expiration date."""
        return bool(self.expires_on and self.expires_on < date.today())

    @property
    def is_expiring_soon(self) -> bool:
        """Return True if the record expires within the reminder window."""
        if not self.expires_on:
            return False
        reminder_window = self.immunization_type.reminder_days_before
        today = date.today()
        return today <= self.expires_on <= today + timedelta(days=reminder_window)
