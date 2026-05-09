"""Centralized configuration and environment loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


_BASE_DIR = Path(__file__).resolve().parent.parent
_ENV_PATH = _BASE_DIR / ".env"
load_dotenv(_ENV_PATH)


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    GEMINI_API_KEY: str
    FIREBASE_STORAGE_BUCKET: str
    GEMINI_MODEL: str = "gemini-1.5-pro"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"


def _read_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _read_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    """Build and validate settings once at startup."""
    return Settings(
        GEMINI_API_KEY=_read_required_env("GEMINI_API_KEY"),
        FIREBASE_STORAGE_BUCKET=_read_required_env("FIREBASE_STORAGE_BUCKET"),
        GEMINI_MODEL=os.getenv("GEMINI_MODEL", "gemini-1.5-pro").strip() or "gemini-1.5-pro",
        DEBUG=_read_bool_env("DEBUG", False),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO").strip() or "INFO",
    )


settings = load_settings()
