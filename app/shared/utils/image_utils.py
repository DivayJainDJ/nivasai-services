"""
Image utilities for processing complaint photos and satellite imagery.
"""

from typing import Optional
import base64


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode image file to base64 string.

    Args:
        image_path: Path to image file

    Returns:
        Base64 encoded image string
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_image_mime_type(image_path: str) -> str:
    """
    Determine MIME type from image file extension.

    Args:
        image_path: Path to image file

    Returns:
        MIME type string
    """
    extension = image_path.lower().split(".")[-1]
    mime_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    return mime_types.get(extension, "image/jpeg")
