"""Pricing schema definitions."""

from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PricingQuoteRequest(BaseModel):
    """Input payload for generating a reservation quote."""

    reservation_id: uuid.UUID
    promotion_code: str | None = None


class PricingLineRead(BaseModel):
    """Individual line item within a pricing quote."""

    description: str
    amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class PricingQuoteRead(BaseModel):
    """Aggregated pricing response."""

    reservation_id: uuid.UUID
    items: list[PricingLineRead]
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal

    model_config = ConfigDict(from_attributes=True)
