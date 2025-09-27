"""Helpers for redacting PII in exports."""

from __future__ import annotations

import os
from typing import Any

_BOOL_TRUE = {"1", "true", "yes", "on"}
_REDACT_ENABLED = os.getenv("EXPORT_REDACT", "true").lower() in _BOOL_TRUE


def is_redaction_enabled() -> bool:
    return _REDACT_ENABLED


def redact_value(value: str | None, placeholder: str = "REDACTED") -> str | None:
    if value is None or value == "":
        return value
    return placeholder


def mask_name(first: str | None, last: str | None) -> str:
    if not _REDACT_ENABLED:
        return " ".join(part for part in (first, last) if part)
    return "REDACTED"


def mask_email(value: str | None) -> str | None:
    if not value or "@" not in value:
        return value
    local, _, domain = value.partition("@")
    if not local:
        return "***@" + domain
    return f"{local[0]}***@{domain}"


def mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    digits = [ch for ch in value if ch.isdigit()]
    if len(digits) < 4:
        return "***"
    return f"***-***-{''.join(digits[-4:])}"


def redact_owner_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with sensitive fields obfuscated when enabled."""
    if not _REDACT_ENABLED:
        return payload
    masked = dict(payload)
    user = masked.get("user")
    if isinstance(user, dict):
        user = dict(user)
        user["email"] = mask_email(user.get("email"))
        user["phone_number"] = mask_phone(user.get("phone_number"))
        masked["user"] = user
    for key in ("email",):
        if key in masked:
            masked[key] = mask_email(masked.get(key))
    for key in ("phone", "phone_number"):
        if key in masked:
            masked[key] = mask_phone(masked.get(key))
    for key in ("address1", "address2", "address_line1", "address_line2"):
        if key in masked:
            masked[key] = redact_value(masked.get(key))
    return masked


__all__ = [
    "is_redaction_enabled",
    "mask_email",
    "mask_phone",
    "mask_name",
    "redact_owner_payload",
]
