"""Logging filters that scrub sensitive content."""

from __future__ import annotations

import logging
import re

_SENSITIVE_PATTERN = re.compile(
    r"(Authorization: Bearer\s+[\w\.-]+|access_token\"\s*:\s*\"[^\"]+\"|password\"\s*:\s*\"[^\"]+\")",
    re.IGNORECASE,
)


class SensitiveFilter(logging.Filter):
    """Replace sensitive tokens in log messages with a redaction marker."""

    def filter(
        self, record: logging.LogRecord
    ) -> bool:  # pragma: no cover - logging side effect
        if isinstance(record.msg, str):
            record.msg = _SENSITIVE_PATTERN.sub("**REDACTED**", record.msg)
        return True


__all__ = ["SensitiveFilter"]
