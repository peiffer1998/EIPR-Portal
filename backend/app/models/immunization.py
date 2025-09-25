"""Immunization models for the health track."""

from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - imported for typing only
    from app.models import Pet, User


class ImmunizationStatus(str, enum.Enum):
    """Lifecycle state for an immunization record."""

    PENDING = "pending"
    CURRENT = "current"
    EXPIRING = "expiring"
    EXPIRED = "expired"


class ImmunizationType(TimestampMixin, Base):
    """Account-scoped immunization configuration."""

    __tablename__ = "immunization_types"
    __table_args__ = (
        UniqueConstraint("account_id", "name", name="uq_immunization_type_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_valid_days: Mapped[int | None] = mapped_column(Integer(), nullable=True)

    records: Mapped[list["ImmunizationRecord"]] = relationship(
        "ImmunizationRecord",
        back_populates="immunization_type",
        cascade="all, delete-orphan",
    )


class ImmunizationRecord(TimestampMixin, Base):
    """Recorded immunization entry for a pet."""

    __tablename__ = "immunization_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("immunization_types.id", ondelete="CASCADE"), nullable=False
    )
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)
    expires_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[ImmunizationStatus] = mapped_column(
        Enum(ImmunizationStatus), default=ImmunizationStatus.PENDING, nullable=False
    )
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text())

    immunization_type: Mapped[ImmunizationType] = relationship(
        "ImmunizationType", back_populates="records"
    )
    pet: Mapped["Pet"] = relationship("Pet", back_populates="immunization_records")
    verified_by: Mapped["User | None"] = relationship("User")
