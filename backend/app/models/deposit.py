"""Deposit tracking models."""

from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing only imports
    from app.models.account import Account
    from app.models.owner_profile import OwnerProfile
    from app.models.reservation import Reservation


class DepositStatus(str, enum.Enum):
    """Lifecycle for reservation deposits."""

    HELD = "held"
    CONSUMED = "consumed"
    REFUNDED = "refunded"
    FORFEITED = "forfeited"


class Deposit(TimestampMixin, Base):
    """Monetary deposit tied to a reservation."""

    __tablename__ = "deposits"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("owner_profiles.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[DepositStatus] = mapped_column(Enum(DepositStatus), nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="deposits")
    reservation: Mapped["Reservation"] = relationship("Reservation", backref="deposits")
    owner: Mapped["OwnerProfile"] = relationship(
        "OwnerProfile", back_populates="deposits"
    )
