"""Retry helpers for Gemini and parsing resiliency."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")


class RetryableGeminiError(Exception):
    """Transient model invocation failure."""


class RetryableParseError(Exception):
    """Model responded but output could not be parsed/validated."""


class RetryConfig:
    """Default retry configuration for structured generation."""

    MAX_ATTEMPTS = 4
    INITIAL_WAIT_SECONDS = 1
    MAX_WAIT_SECONDS = 8


def with_exponential_retry(
    *,
    max_attempts: int = RetryConfig.MAX_ATTEMPTS,
    initial_wait_seconds: int = RetryConfig.INITIAL_WAIT_SECONDS,
    max_wait_seconds: int = RetryConfig.MAX_WAIT_SECONDS,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry on transient Gemini and parse failures with exponential backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            reraise=True,
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_wait_seconds,
                min=initial_wait_seconds,
                max=max_wait_seconds,
            ),
            retry=retry_if_exception_type(
                (RetryableGeminiError, RetryableParseError, TimeoutError)
            ),
        )
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = [
    "RetryConfig",
    "RetryError",
    "RetryableGeminiError",
    "RetryableParseError",
    "with_exponential_retry",
]
