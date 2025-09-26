"""Minimal S3 helper suitable for local and test environments."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class S3ClientError(RuntimeError):
    """Raised when storage operations fail."""


@dataclass
class StoredObject:
    """Metadata for an object stored via the helper."""

    key: str
    path: Path
    size: int
    content_type: str
    cache_control: str | None = None
    tags: dict[str, str] = field(default_factory=dict)


class S3Client:
    """Very small, file-system backed S3 facade for tests and local dev."""

    def __init__(
        self,
        bucket: str,
        *,
        endpoint_url: str | None = None,
        root: Path | None = None,
        default_cache_seconds: int = 0,
    ) -> None:
        if not bucket:
            raise S3ClientError("S3 bucket is not configured")
        self.bucket = bucket
        self._endpoint_url = endpoint_url.rstrip("/") if endpoint_url else None
        self._root = (root or Path.cwd() / ".storage") / bucket
        self._root.mkdir(parents=True, exist_ok=True)
        self._objects: dict[str, StoredObject] = {}
        self._default_cache_seconds = default_cache_seconds

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _normalise_key(self, key: str) -> str:
        normalised = key.lstrip("/")
        if not normalised:
            raise S3ClientError("Storage object key cannot be empty")
        return normalised

    def _path_for(self, key: str) -> Path:
        normalised = self._normalise_key(key)
        path = self._root / normalised
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def put_object_with_cache(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str,
        cache_seconds: int | None = None,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Write an object applying cache headers and optional tagging."""

        path = self._path_for(key)
        path.write_bytes(data)
        cache_control = (
            f"public, max-age={cache_seconds or self._default_cache_seconds}, immutable"
            if (cache_seconds or self._default_cache_seconds) > 0
            else None
        )
        stored = StoredObject(
            key=self._normalise_key(key),
            path=path,
            size=len(data),
            content_type=content_type,
            cache_control=cache_control,
            tags=dict(tags or {}),
        )
        self._objects[stored.key] = stored

    def get_object_bytes(self, key: str) -> bytes:
        path = self._path_for(key)
        try:
            raw = path.read_bytes()
        except FileNotFoundError as exc:  # pragma: no cover - defensive
            raise S3ClientError(f"Object {key} not found") from exc
        self._ensure_object_record(key, len(raw))
        return raw

    def put_object_tagging(self, key: str, tags: dict[str, str]) -> None:
        stored = self._objects.get(self._normalise_key(key))
        if not stored:
            stored = self._ensure_object_record(key, size=0)
        stored.tags.update(tags)

    def build_object_url(self, key: str) -> str:
        normalised = self._normalise_key(key)
        if self._endpoint_url:
            return f"{self._endpoint_url}/{self.bucket}/{normalised}"
        return f"/{self.bucket}/{normalised}"

    def get_object_metadata(self, key: str) -> StoredObject | None:
        return self._objects.get(self._normalise_key(key))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_object_record(self, key: str, size: int) -> StoredObject:
        normalised = self._normalise_key(key)
        existing = self._objects.get(normalised)
        if existing:
            return existing
        stored = StoredObject(
            key=normalised,
            path=self._path_for(normalised),
            size=size,
            content_type="application/octet-stream",
        )
        self._objects[normalised] = stored
        return stored


def build_s3_client(**overrides: Any) -> S3Client:
    """Factory that honours application settings."""

    from app.core.config import get_settings

    settings = get_settings()
    bucket = overrides.get("bucket") or settings.s3_bucket
    if not bucket:
        raise S3ClientError("S3 bucket is not configured")
    return S3Client(
        bucket,
        endpoint_url=overrides.get("endpoint_url") or settings.s3_endpoint_url,
        root=overrides.get("root"),
        default_cache_seconds=settings.s3_cache_seconds,
    )
