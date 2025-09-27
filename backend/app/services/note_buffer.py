"""Simple in-memory buffers for owner and pet notes (development placeholder)."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from typing import Any, Deque
from uuid import UUID, uuid4

_MAX_NOTES = 200

_pet_notes: dict[UUID, Deque[dict[str, Any]]] = {}
_owner_notes: dict[UUID, Deque[dict[str, Any]]] = {}


def _get_buffer(
    store: dict[UUID, Deque[dict[str, Any]]], key: UUID
) -> Deque[dict[str, Any]]:
    buf = store.get(key)
    if buf is None:
        buf = deque(maxlen=_MAX_NOTES)
        store[key] = buf
    return buf


def list_pet_notes(pet_id: UUID) -> list[dict[str, Any]]:
    return list(_get_buffer(_pet_notes, pet_id))


def add_pet_note(
    pet_id: UUID, *, text: str, author_id: UUID | None = None
) -> dict[str, Any]:
    entry = {
        "id": uuid4(),
        "pet_id": pet_id,
        "text": text,
        "author_id": author_id,
        "created_at": datetime.now(UTC),
    }
    buf = _get_buffer(_pet_notes, pet_id)
    buf.append(entry)
    return entry


def list_owner_notes(owner_id: UUID) -> list[dict[str, Any]]:
    return list(_get_buffer(_owner_notes, owner_id))


def add_owner_note(
    owner_id: UUID, *, text: str, author_id: UUID | None = None
) -> dict[str, Any]:
    entry = {
        "id": uuid4(),
        "owner_id": owner_id,
        "text": text,
        "author_id": author_id,
        "created_at": datetime.now(UTC),
    }
    buf = _get_buffer(_owner_notes, owner_id)
    buf.append(entry)
    return entry


def clear_all() -> None:
    """Utility for tests to reset buffers."""
    _pet_notes.clear()
    _owner_notes.clear()
