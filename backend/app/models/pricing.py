"""Pricing-related ORM models."""

from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - runtime-only import
    from app.models.account import Account


class PriceRuleType(str, enum.Enum):
    """Supported dynamic pricing rule types."""

    PEAK_DATE = "peak_date"
    LATE_CHECKOUT = "late_checkout"
    LODGING_SURCHARGE = "lodging_surcharge"
    VIP = "vip"


class PriceRule(TimestampMixin, Base):
    """Account-scoped pricing rule with JSON parameters."""

    __tablename__ = "price_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[PriceRuleType] = mapped_column(
        Enum(PriceRuleType), nullable=False
    )
    params: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        default=dict,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="price_rules")


class PromotionKind(str, enum.Enum):
    """Type of discount promotion."""

    PERCENT = "percent"
    AMOUNT = "amount"


class Promotion(TimestampMixin, Base):
    """Account promotion codes."""

    __tablename__ = "promotions"
    __table_args__ = (
        UniqueConstraint("account_id", "code", name="uq_promotions_account_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[PromotionKind] = mapped_column(Enum(PromotionKind), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    starts_on: Mapped[Date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[Date | None] = mapped_column(Date, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="promotions")
