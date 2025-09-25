"""Account model representing a tenant/business entity."""
from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Account(TimestampMixin, Base):
    """A tenant account (e.g., a pet resort location group)."""

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, unique=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    locations: Mapped[list["Location"]] = relationship(
        "Location", back_populates="account", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="account", cascade="all, delete-orphan"
    )
