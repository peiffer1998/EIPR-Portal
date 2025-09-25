"""Service catalog models for offerings and retail items."""
from __future__ import annotations

import enum
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin
from app.models.reservation import ReservationType


class ServiceCatalogKind(str, enum.Enum):
    """Categories for catalog entries."""

    SERVICE = "service"
    RETAIL = "retail"


class ServiceCatalogItem(TimestampMixin, Base):
    """Represents a billable service or retail product."""

    __tablename__ = "service_catalog_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024))
    kind: Mapped[ServiceCatalogKind] = mapped_column(Enum(ServiceCatalogKind), nullable=False)
    reservation_type: Mapped[ReservationType | None] = mapped_column(
        Enum(ReservationType), nullable=True
    )
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sku: Mapped[str | None] = mapped_column(String(64), unique=True)
