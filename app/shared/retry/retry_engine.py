"""
Retry engine for resilient API calls and failure handling.
"""

import json
from typing import Callable, TypeVar, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_result,
)

T = TypeVar("T")


def retry_on_failure(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """Decorator for retrying with exponential backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_wait,
                min=initial_wait,
                max=max_wait,
            ),
            reraise=True,
        )
        def wrapper(*args, **kwargs) -> T:
            return func(*args, **kwargs)

        return wrapper

    return decorator


def retry_on_malformed_json(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
) -> Callable:
    """Decorator for retrying on malformed JSON responses."""

    def decorator(func: Callable[..., Optional[str]]) -> Callable[..., Optional[str]]:
        def is_invalid_json(result):
            if result is None or not isinstance(result, str):
                return True
            try:
                json.loads(result)
                return False
            except (json.JSONDecodeError, ValueError):
                return True

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_wait,
                min=initial_wait,
                max=max_wait,
            ),
            retry=retry_if_result(is_invalid_json),
            reraise=True,
        )
        def wrapper(*args, **kwargs) -> Optional[str]:
            return func(*args, **kwargs)

        return wrapper

    return decorator


class RetryConfig:
    """Configuration for retry behavior."""

    MAX_ATTEMPTS = 3
    INITIAL_WAIT = 1.0
    MAX_WAIT = 10.0
