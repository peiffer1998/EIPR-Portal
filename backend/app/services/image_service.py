"""Utilities for hashing and transforming uploaded images."""

from __future__ import annotations

import hashlib
from io import BytesIO
from PIL import Image, UnidentifiedImageError


def hash_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest for the given bytes."""

    return hashlib.sha256(data).hexdigest()


def _should_convert_image(image: Image.Image, max_width: int) -> bool:
    width, height = image.size
    return max(width, height) > max_width


def _resize_image(image: Image.Image, max_width: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_width:
        return image
    scale = max_width / float(longest)
    new_size = (max(int(width * scale), 1), max(int(height * scale), 1))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def to_webp(data: bytes, max_width: int, quality: int) -> tuple[bytes, int, int]:
    """Convert image bytes to WebP, constraining the maximum width.

    Returns a tuple of (webp_bytes, width, height). If the input is not an image,
    the original bytes are returned with zero dimensions recorded.
    """

    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            if image.mode not in {"RGB", "RGBA", "LA"}:
                image = (
                    image.convert("RGBA")
                    if "A" in image.getbands()
                    else image.convert("RGB")
                )
            resized = _resize_image(image, max_width)
            buffer = BytesIO()
            quality_value = max(1, min(quality, 100))
            if resized.mode == "RGBA":
                resized.save(
                    buffer,
                    format="WEBP",
                    quality=quality_value,
                    method=6,
                    lossless=False,
                )
            else:
                resized.save(
                    buffer,
                    format="WEBP",
                    quality=quality_value,
                    method=6,
                )
            output = buffer.getvalue()
            width, height = resized.size
            return output, width, height
    except (UnidentifiedImageError, OSError):
        return data, 0, 0

    return data, 0, 0
