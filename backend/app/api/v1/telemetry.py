"""Telemetry ingestion endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.services import telemetry_buffer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryEvent(BaseModel):
    ts: int = Field(..., ge=0)
    type: str = Field(..., min_length=1, max_length=128)
    request_id: str | None = Field(default=None, alias="requestId")
    message: str | None = None
    meta: Any = None

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


class TelemetryBatch(BaseModel):
    events: list[TelemetryEvent] = Field(default_factory=list)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(batch: TelemetryBatch) -> dict[str, int]:
    """Accept a batch of telemetry events and buffer them in memory."""
    if not batch.events:
        return {"accepted": 0}

    telemetry_buffer.push(event.as_dict() for event in batch.events)
    logger.debug("Accepted %s telemetry events", len(batch.events))
    return {"accepted": len(batch.events)}


@router.get("", tags=["telemetry"])
async def list_telemetry(limit: int = 200) -> dict[str, list[dict[str, Any]]]:
    """Return recent telemetry events for debugging."""
    events = telemetry_buffer.snapshot(limit)
    return {"events": events}
