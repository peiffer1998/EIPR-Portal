"""Tests for document finalisation and WebP handling."""

from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path
from typing import cast

import os

import pytest
from httpx import AsyncClient
from PIL import Image

from app.api import deps
from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.integrations import S3Client
from app.models.document import Document


async def _authenticate(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": email, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _clear_storage(bucket: str) -> None:
    root = Path.cwd() / ".storage" / bucket
    if root.exists():
        for path in sorted(root.glob("**/*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                try:
                    path.rmdir()
                except OSError:
                    pass


def _create_image_bytes(size: tuple[int, int] = (2048, 1536)) -> bytes:
    image = Image.new("RGB", size, color=(120, 180, 30))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


@pytest.mark.asyncio()
async def test_finalize_generates_webp_and_reuses_existing(
    app_context: dict[str, object],
) -> None:
    client = cast(AsyncClient, app_context["client"])
    manager_email = cast(str, app_context["manager_email"])
    manager_password = cast(str, app_context["manager_password"])

    token = await _authenticate(client, manager_email, manager_password)

    settings = get_settings()
    assert settings.s3_bucket is not None

    # Ensure clean slate for the local storage stub and recreate cached client
    _clear_storage(settings.s3_bucket)
    deps._build_s3_client.cache_clear()
    s3_client: S3Client = deps.get_s3_client()

    upload_key = f"uploads/{uuid.uuid4().hex}.jpg"
    original_bytes = _create_image_bytes()
    s3_client.put_object_with_cache(
        upload_key,
        original_bytes,
        content_type="image/jpeg",
        cache_seconds=0,
    )

    response = await client.post(
        "/api/v1/documents/finalize",
        json={
            "upload_key": upload_key,
            "file_name": "vaccination-card.jpg",
            "content_type": "image/jpeg",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["url_web"] is not None
    assert payload["sha256"]
    assert payload["content_type_web"] == "image/webp"

    web_url = payload["url_web"]
    document_id = uuid.UUID(payload["id"])

    sessionmaker = get_sessionmaker(os.environ["DATABASE_URL"])
    async with sessionmaker() as session:
        stored = await session.get(Document, document_id)
        assert stored is not None
        assert stored.sha256 == payload["sha256"]
        assert stored.object_key_web is not None
        assert stored.bytes_web is not None
        assert stored.width is not None and stored.height is not None

    web_key = stored.object_key_web if stored else None
    assert web_key is not None
    metadata_web = s3_client.get_object_metadata(web_key)
    assert metadata_web is not None
    assert (
        metadata_web.cache_control is not None
        and "max-age" in metadata_web.cache_control
    )
    assert metadata_web.content_type == "image/webp"

    original_meta = s3_client.get_object_metadata(upload_key)
    assert original_meta is not None
    assert original_meta.tags.get("retain") == str(settings.image_keep_original_days)

    second_upload_key = f"uploads/{uuid.uuid4().hex}.jpg"
    s3_client.put_object_with_cache(
        second_upload_key,
        original_bytes,
        content_type="image/jpeg",
        cache_seconds=0,
    )

    response_dup = await client.post(
        "/api/v1/documents/finalize",
        json={
            "upload_key": second_upload_key,
            "file_name": "vaccination-card.jpg",
            "content_type": "image/jpeg",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response_dup.status_code == 201
    payload_dup = response_dup.json()
    assert payload_dup["url_web"] == web_url
    assert payload_dup["sha256"] == payload["sha256"]

    web_path = Path.cwd() / ".storage" / settings.s3_bucket / web_key
    assert web_path.exists()

    orig_path = Path.cwd() / ".storage" / settings.s3_bucket / upload_key
    dup_path = Path.cwd() / ".storage" / settings.s3_bucket / second_upload_key
    assert orig_path.exists() and dup_path.exists()
