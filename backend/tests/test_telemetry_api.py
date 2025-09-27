"""Tests for telemetry ingestion endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services import telemetry_buffer

pytestmark = pytest.mark.asyncio


async def test_ingest_buffers_events(app_context: dict[str, object]) -> None:
    telemetry_buffer.clear()
    client = app_context["client"]
    assert isinstance(client, AsyncClient)
    payload = {
        "events": [
            {
                "ts": 1,
                "type": "vital.LCP",
                "requestId": "abc-123",
                "message": "Largest Contentful Paint",
                "meta": {"value": 2500},
            }
        ]
    }

    response = await client.post("/api/v1/telemetry", json=payload)

    assert response.status_code == 202
    assert response.json() == {"accepted": 1}

    events = telemetry_buffer.snapshot()
    assert len(events) == 1
    assert events[0]["type"] == "vital.LCP"
    assert events[0]["requestId"] == "abc-123"


async def test_list_endpoint_returns_recent_events(
    app_context: dict[str, object],
) -> None:
    telemetry_buffer.clear()
    client = app_context["client"]
    assert isinstance(client, AsyncClient)

    telemetry_buffer.push(
        [
            {
                "ts": 5,
                "type": "http.timing",
                "requestId": "req-789",
                "meta": {"ms": 120},
            }
        ]
    )

    response = await client.get("/api/v1/telemetry?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"]
    assert payload["events"][0]["requestId"] == "req-789"
