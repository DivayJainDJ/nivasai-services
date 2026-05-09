"""Satellite image ingestion and validation utilities."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, UnidentifiedImageError

ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 12 * 1024 * 1024


class SatelliteImageError(Exception):
    """Raised when satellite image is invalid."""


def validate_satellite_image(image_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Validate uploaded satellite image and return normalized payload."""
    if content_type not in ALLOWED_MIME_TYPES:
        raise SatelliteImageError("Unsupported image format; allowed: jpg, jpeg, png, webp")
    if not image_bytes:
        raise SatelliteImageError("Satellite image is empty")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise SatelliteImageError("Satellite image exceeds 12MB limit")

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise SatelliteImageError("Invalid or corrupted satellite image") from exc

    return image_bytes, content_type
