"""In-memory buffer for recent telemetry events."""

from __future__ import annotations

from collections import deque
from typing import Any, Deque, Iterable, Mapping

_MAX_EVENTS = 1000
_BUFFER: Deque[dict[str, Any]] = deque(maxlen=_MAX_EVENTS)


def push(events: Iterable[Mapping[str, Any]]) -> None:
    """Store a set of telemetry events in FIFO order."""
    for event in events:
        _BUFFER.append(dict(event))


def snapshot(limit: int = 200) -> list[dict[str, Any]]:
    """Return up to ``limit`` most recent telemetry events."""
    if limit <= 0:
        return []
    if limit >= len(_BUFFER):
        return list(_BUFFER)
    return list(_BUFFER)[-limit:]


def clear() -> None:
    """Clear the telemetry buffer (mainly for tests)."""
    _BUFFER.clear()
