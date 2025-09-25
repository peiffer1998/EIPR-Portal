"""Reporting schemas."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.reservation import ReservationType


class OccupancyEntry(BaseModel):
    """Daily occupancy data for a location and reservation type."""

    location_id: uuid.UUID
    location_name: str
    reservation_type: ReservationType
    date: date
    capacity: int | None = None
    booked: int
    available: int | None = None
    occupancy_rate: float | None = None


class RevenueEntry(BaseModel):
    """Revenue aggregated over a period for a location."""

    location_id: uuid.UUID
    location_name: str
    period_start: date
    total_revenue: Decimal

    model_config = ConfigDict(from_attributes=True)


class RevenueReport(BaseModel):
    """Collection of revenue entries and grand total."""

    entries: list[RevenueEntry]
    grand_total: Decimal
