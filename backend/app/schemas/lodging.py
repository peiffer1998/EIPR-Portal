"""Schemas for lodging runs."""

from __future__ import annotations

from pydantic import BaseModel


class RunRead(BaseModel):
    """Lightweight representation of a lodging run/kennel."""

    id: str
    name: str
    kind: str | None = None
    capacity: int | None = None
