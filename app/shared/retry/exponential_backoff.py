"""
Exponential backoff configuration.
"""


class ExponentialBackoffConfig:
    """Configuration for exponential backoff strategy."""

    INITIAL_DELAY = 1.0  # seconds
    MAX_DELAY = 60.0  # seconds
    MULTIPLIER = 2.0
    MAX_RETRIES = 5

    @staticmethod
    def calculate_delay(attempt: int) -> float:
        """Calculate delay for attempt number."""
        delay = ExponentialBackoffConfig.INITIAL_DELAY * (
            ExponentialBackoffConfig.MULTIPLIER ** attempt
        )
        return min(delay, ExponentialBackoffConfig.MAX_DELAY)
