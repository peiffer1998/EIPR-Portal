"""Payroll and compensation models: time clock, tips, commissions, pay periods, pay rates."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Text

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models import Account, Location, User
    from app.models.grooming import GroomingAppointment

JSONB_TYPE = JSONB(astext_type=Text()).with_variant(JSON(), "sqlite")


class TipPolicy(str, enum.Enum):
    DIRECT_TO_STAFF = "direct_to_staff"
    POOLED_BY_HOURS = "pooled_by_hours"
    POOLED_EQUAL = "pooled_equal"
    APPOINTMENT_DIRECT = "appointment_direct"


class PayrollPeriod(TimestampMixin, Base):
    __tablename__ = "payroll_periods"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "location_id",
            "starts_on",
            "ends_on",
            name="uq_payroll_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL")
    )
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    totals: Mapped[dict | None] = mapped_column(JSONB_TYPE)

    account: Mapped["Account"] = relationship("Account")
    location: Mapped["Location | None"] = relationship("Location")


class PayRateHistory(TimestampMixin, Base):
    __tablename__ = "pay_rate_history"
    __table_args__ = (Index("ix_pay_rate_history_user", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    effective_on: Mapped[date] = mapped_column(Date, nullable=False)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    ended_on: Mapped[date | None] = mapped_column(Date)

    account: Mapped["Account"] = relationship("Account")
    user: Mapped["User"] = relationship("User")


class TimeClockPunch(TimestampMixin, Base):
    __tablename__ = "time_clock_punches"
    __table_args__ = (
        Index("ix_timeclock_user_open", "user_id"),
        Index("ix_timeclock_account_date", "account_id", "clock_in_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    clock_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    clock_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rounded_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    rounded_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    minutes_worked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="web")
    note: Mapped[str | None] = mapped_column(String(512))
    payroll_period_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payroll_periods.id", ondelete="SET NULL")
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    account: Mapped["Account"] = relationship("Account")
    location: Mapped["Location"] = relationship("Location")
    user: Mapped["User"] = relationship("User")
    payroll_period: Mapped["PayrollPeriod | None"] = relationship("PayrollPeriod")


class TipTransaction(TimestampMixin, Base):
    __tablename__ = "tip_transactions"
    __table_args__ = (Index("ix_tip_tx_date_location", "date", "location_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="card")
    policy: Mapped[TipPolicy] = mapped_column(Enum(TipPolicy), nullable=False)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("grooming_appointments.id", ondelete="SET NULL")
    )
    payment_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_transactions.id", ondelete="SET NULL")
    )
    payroll_period_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payroll_periods.id", ondelete="SET NULL")
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(String(512))

    shares: Mapped[list["TipShare"]] = relationship(
        "TipShare", back_populates="tip_transaction", cascade="all, delete-orphan"
    )


class TipShare(TimestampMixin, Base):
    __tablename__ = "tip_shares"
    __table_args__ = (
        UniqueConstraint(
            "tip_transaction_id", "user_id", name="uq_tip_share_recipient"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tip_transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tip_transactions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False, default="direct")

    tip_transaction: Mapped["TipTransaction"] = relationship("TipTransaction")
    user: Mapped["User"] = relationship("User")


class CommissionPayout(TimestampMixin, Base):
    __tablename__ = "commission_payouts"
    __table_args__ = (
        UniqueConstraint("appointment_id", name="uq_commission_by_appointment"),
        Index("ix_commission_specialist", "specialist_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grooming_appointments.id", ondelete="CASCADE"), nullable=False
    )
    specialist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("specialists.id", ondelete="CASCADE"), nullable=False
    )
    basis_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payroll_period_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payroll_periods.id", ondelete="SET NULL")
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    snapshot: Mapped[dict | None] = mapped_column(JSONB_TYPE)

    account: Mapped["Account"] = relationship("Account")
    location: Mapped["Location"] = relationship("Location")
    payroll_period: Mapped["PayrollPeriod | None"] = relationship("PayrollPeriod")
    appointment: Mapped["GroomingAppointment"] = relationship("GroomingAppointment")
