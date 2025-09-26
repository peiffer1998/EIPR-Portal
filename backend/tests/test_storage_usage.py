"""Tests for storage usage reporting."""

from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path
from typing import cast

import pytest
from httpx import AsyncClient
from PIL import Image

from app.api import deps
from app.core.config import get_settings
from app.integrations import S3Client


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


def _jpeg_bytes() -> bytes:
    image = Image.new("RGB", (1024, 768), color=(10, 140, 200))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


@pytest.mark.asyncio()
async def test_storage_usage_endpoint_reports_totals(
    app_context: dict[str, object],
) -> None:
    client = cast(AsyncClient, app_context["client"])
    manager_email = cast(str, app_context["manager_email"])
    manager_password = cast(str, app_context["manager_password"])

    token = await _authenticate(client, manager_email, manager_password)

    settings = get_settings()
    assert settings.s3_bucket is not None

    _clear_storage(settings.s3_bucket)
    deps._build_s3_client.cache_clear()
    s3_client: S3Client = deps.get_s3_client()

    image_bytes = _jpeg_bytes()
    upload_key_image = f"uploads/{uuid.uuid4().hex}.jpg"
    s3_client.put_object_with_cache(
        upload_key_image,
        image_bytes,
        content_type="image/jpeg",
        cache_seconds=0,
    )

    response_image = await client.post(
        "/api/v1/documents/finalize",
        json={
            "upload_key": upload_key_image,
            "file_name": "boarding-photo.jpg",
            "content_type": "image/jpeg",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response_image.status_code == 201
    image_payload = response_image.json()

    text_bytes = b"boarding instructions"
    upload_key_text = f"uploads/{uuid.uuid4().hex}.txt"
    s3_client.put_object_with_cache(
        upload_key_text,
        text_bytes,
        content_type="text/plain",
        cache_seconds=0,
    )

    response_text = await client.post(
        "/api/v1/documents/finalize",
        json={
            "upload_key": upload_key_text,
            "file_name": "instructions.txt",
            "content_type": "text/plain",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response_text.status_code == 201

    usage_response = await client.get(
        "/api/v1/storage/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert usage_response.status_code == 200
    usage = usage_response.json()

    web_key = image_payload["object_key_web"]
    assert web_key is not None

    image_original_meta = s3_client.get_object_metadata(upload_key_image)
    text_original_meta = s3_client.get_object_metadata(upload_key_text)
    web_meta = s3_client.get_object_metadata(web_key)

    expected_original = (image_original_meta.size if image_original_meta else 0) + (
        text_original_meta.size if text_original_meta else 0
    )
    expected_web = web_meta.size if web_meta else 0

    assert usage["total_count"] == 2
    assert usage["total_original_bytes"] == expected_original
    assert usage["total_web_bytes"] == expected_web

    by_type = usage["by_type"]
    assert by_type["image/jpeg"]["count"] == 1
    assert by_type["image/jpeg"]["bytes"] == (
        image_original_meta.size if image_original_meta else 0
    )
    assert by_type["image/webp"]["count"] == 1
    assert by_type["image/webp"]["bytes"] == expected_web
    assert by_type["text/plain"]["count"] == 1
    assert by_type["text/plain"]["bytes"] == (
        text_original_meta.size if text_original_meta else 0
    )
