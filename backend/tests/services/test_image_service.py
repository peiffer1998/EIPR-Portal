"""Tests for image transformation utilities."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.services.image_service import hash_bytes, to_webp


def _create_sample_jpeg(width: int = 2400, height: int = 1600) -> bytes:
    image = Image.new("RGB", (width, height), color=(200, 90, 10))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return buffer.getvalue()


def test_hash_bytes_is_deterministic() -> None:
    sample = b"example-bytes"
    assert hash_bytes(sample) == hash_bytes(sample)


def test_to_webp_resizes_and_converts() -> None:
    original = _create_sample_jpeg()
    webp_bytes, width, height = to_webp(original, max_width=1200, quality=80)

    assert webp_bytes != original
    assert max(width, height) <= 1200
    assert width > 0 and height > 0
    assert len(webp_bytes) < len(original)


def test_to_webp_returns_original_for_non_images() -> None:
    raw = b"not-an-image"
    output, width, height = to_webp(raw, max_width=800, quality=80)
    assert output == raw
    assert width == 0 and height == 0
