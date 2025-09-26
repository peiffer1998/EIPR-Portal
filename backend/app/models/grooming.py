"""Grooming domain models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Time,
    UniqueConstraint,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only imports
    from app.models import Account, Invoice, Location, OwnerProfile, Pet, User


class CommissionType(str, enum.Enum):
    """How specialist commission should be calculated."""

    PERCENT = "percent"
    AMOUNT = "amount"


class GroomingAppointmentStatus(str, enum.Enum):
    """Lifecycle states for grooming appointments."""

    REQUESTED = "requested"
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"
    NO_SHOW = "no_show"


class Specialist(TimestampMixin, Base):
    """Grooming specialist configuration."""

    __tablename__ = "specialists"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    commission_type: Mapped[CommissionType] = mapped_column(
        Enum(CommissionType), default=CommissionType.PERCENT, nullable=False
    )
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=Decimal("0.00")
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped["Account"] = relationship("Account")
    user: Mapped["User | None"] = relationship("User")
    location: Mapped["Location"] = relationship("Location")
    schedules: Mapped[list["SpecialistSchedule"]] = relationship(
        "SpecialistSchedule",
        back_populates="specialist",
        cascade="all, delete-orphan",
    )
    time_off_entries: Mapped[list["SpecialistTimeOff"]] = relationship(
        "SpecialistTimeOff",
        back_populates="specialist",
        cascade="all, delete-orphan",
    )
    appointments: Mapped[list["GroomingAppointment"]] = relationship(
        "GroomingAppointment",
        back_populates="specialist",
        cascade="all, delete-orphan",
    )


class SpecialistSchedule(TimestampMixin, Base):
    """Weekly recurring availability for a specialist."""

    __tablename__ = "specialist_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialists.id", ondelete="CASCADE"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(nullable=False)
    start_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    end_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)

    specialist: Mapped["Specialist"] = relationship(
        "Specialist", back_populates="schedules"
    )


class SpecialistTimeOff(TimestampMixin, Base):
    """One-off time blocks where a specialist is unavailable."""

    __tablename__ = "specialist_time_off"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialists.id", ondelete="CASCADE"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))

    specialist: Mapped["Specialist"] = relationship(
        "Specialist", back_populates="time_off_entries"
    )


class GroomingService(TimestampMixin, Base):
    """Catalog entry for a grooming service offering."""

    __tablename__ = "grooming_services"
    __table_args__ = (
        UniqueConstraint("account_id", "code", name="uq_grooming_service_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_duration_minutes: Mapped[int] = mapped_column(nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    appointments: Mapped[list["GroomingAppointment"]] = relationship(
        "GroomingAppointment",
        back_populates="service",
    )


class GroomingAddon(TimestampMixin, Base):
    """Additional service add-ons for grooming appointments."""

    __tablename__ = "grooming_addons"
    __table_args__ = (
        UniqueConstraint("account_id", "code", name="uq_grooming_addon_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    add_duration_minutes: Mapped[int] = mapped_column(nullable=False, default=0)
    add_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    appointments: Mapped[list["GroomingAppointment"]] = relationship(
        "GroomingAppointment",
        secondary="grooming_appointment_addons",
        back_populates="addons",
    )


grooming_appointment_addons = Table(
    "grooming_appointment_addons",
    Base.metadata,
    Column(
        "appointment_id",
        ForeignKey("grooming_appointments.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "addon_id",
        ForeignKey("grooming_addons.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class GroomingAppointment(TimestampMixin, Base):
    """Scheduled grooming appointment for a pet."""

    __tablename__ = "grooming_appointments"
    __table_args__ = (
        Index("ix_grooming_appointments_start_at", "start_at"),
        Index("ix_grooming_appointments_specialist", "specialist_id"),
        Index("ix_grooming_appointments_service", "service_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pets.id", ondelete="CASCADE"), nullable=False
    )
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialists.id", ondelete="CASCADE"), nullable=False
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grooming_services.id", ondelete="CASCADE"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[GroomingAppointmentStatus] = mapped_column(
        Enum(GroomingAppointmentStatus),
        nullable=False,
        default=GroomingAppointmentStatus.REQUESTED,
    )
    notes: Mapped[str | None] = mapped_column(String(1024))
    price_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    commission_type: Mapped[CommissionType | None] = mapped_column(
        Enum(CommissionType), nullable=True
    )
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    commission_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )

    account: Mapped["Account"] = relationship("Account")
    owner: Mapped["OwnerProfile"] = relationship("OwnerProfile")
    pet: Mapped["Pet"] = relationship("Pet")
    specialist: Mapped["Specialist"] = relationship(
        "Specialist", back_populates="appointments"
    )
    service: Mapped["GroomingService"] = relationship(
        "GroomingService", back_populates="appointments"
    )
    addons: Mapped[list["GroomingAddon"]] = relationship(
        "GroomingAddon",
        secondary=grooming_appointment_addons,
        back_populates="appointments",
    )
    invoice: Mapped["Invoice | None"] = relationship(
        "Invoice", back_populates="grooming_appointments"
    )


__all__ = [
    "Specialist",
    "SpecialistSchedule",
    "SpecialistTimeOff",
    "GroomingService",
    "GroomingAddon",
    "GroomingAppointment",
    "CommissionType",
    "GroomingAppointmentStatus",
]
