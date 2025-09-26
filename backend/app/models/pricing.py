"""Pricing rules and promotion models."""

from __future__ import annotations

import datetime
import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from app.models.account import Account

JSONB_TYPE = JSONB().with_variant(JSON(), "sqlite")


class PriceRuleType(str, enum.Enum):
    """Enumerates supported price rule handlers."""

    PEAK_DATE = "peak_date"
    LATE_CHECKOUT = "late_checkout"
    LODGING_SURCHARGE = "lodging_surcharge"
    VIP = "vip"


class PromotionKind(str, enum.Enum):
    """Kinds of promotions supported by the pricing engine."""

    PERCENT = "percent"
    AMOUNT = "amount"


class PriceRule(TimestampMixin, Base):
    """Account-scoped pricing rule configuration."""

    __tablename__ = "price_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[PriceRuleType] = mapped_column(
        Enum(PriceRuleType), nullable=False
    )
    params: Mapped[dict[str, Any]] = mapped_column(
        JSONB_TYPE, default=dict, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="price_rules")


class Promotion(TimestampMixin, Base):
    """Promotion code definitions scoped to an account."""

    __tablename__ = "promotions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(nullable=False)
    kind: Mapped[PromotionKind] = mapped_column(Enum(PromotionKind), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    starts_on: Mapped[datetime.date | None] = mapped_column(nullable=True)
    ends_on: Mapped[datetime.date | None] = mapped_column(nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="promotions")
