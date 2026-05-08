"""
Retry engine with exponential backoff for resilient API calls
"""

import asyncio
import random
import time
from typing import Callable, Any, Optional, TypeVar, Union
from functools import wraps
from dataclasses import dataclass
from enum import Enum

from app.shared.logging.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class RetryStrategy(Enum):
    """Retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    JITTER = "jitter"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)
    
    def __post_init__(self):
        """Validate configuration"""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < 0:
            raise ValueError("max_delay must be non-negative")


class RetryState:
    """Track retry state for a single operation"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempt = 0
        self.last_exception: Optional[Exception] = None
        self.total_delay = 0.0
    
    def should_retry(self, exception: Exception) -> bool:
        """Check if operation should be retried"""
        if self.attempt >= self.config.max_retries:
            return False
        
        # Check if exception is retryable
        for retryable_exc in self.config.retryable_exceptions:
            if isinstance(exception, retryable_exc):
                return True
        
        return False
    
    def calculate_delay(self) -> float:
        """Calculate delay before next retry"""
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
        
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * (self.attempt + 1)
        
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** self.attempt)
        
        else:  # JITTER or default
            delay = self.config.base_delay * (self.config.backoff_multiplier ** self.attempt)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * 0.1 * random.random()
            delay += jitter_amount
        
        # Cap at max_delay
        delay = min(delay, self.config.max_delay)
        
        self.total_delay += delay
        return delay
    
    def next_attempt(self) -> None:
        """Prepare for next attempt"""
        self.attempt += 1


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        self.logger = get_logger(__name__)
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator for circuit breaker"""
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            if not self._allow_request():
                raise Exception("Circuit breaker is OPEN")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _allow_request(self) -> bool:
        """Check if request should be allowed"""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False
        
        if self.state == "HALF_OPEN":
            return True
        
        return False
    
    def _on_success(self) -> None:
        """Handle successful request"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            self.logger.info("Circuit breaker transitioning to CLOSED")
    
    def _on_failure(self) -> None:
        """Handle failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "HALF_OPEN":
            self.state = "OPEN"
            self.logger.warning("Circuit breaker transitioning to OPEN")
        elif self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning("Circuit breaker transitioning to OPEN")


def with_retry(config: Optional[RetryConfig] = None):
    """Decorator for retry logic"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            retry_state = RetryState(config)
            logger = get_logger(func.__module__)
            
            while True:
                try:
                    if retry_state.attempt > 0:
                        logger.info(
                            f"Retrying {func.__name__}",
                            attempt=retry_state.attempt + 1,
                            max_attempts=config.max_retries + 1,
                            total_delay=retry_state.total_delay
                        )
                    
                    result = await func(*args, **kwargs)
                    
                    if retry_state.attempt > 0:
                        logger.info(
                            f"Retry successful for {func.__name__}",
                            attempt=retry_state.attempt + 1,
                            total_delay=retry_state.total_delay
                        )
                    
                    return result
                    
                except Exception as e:
                    retry_state.last_exception = e
                    
                    if not retry_state.should_retry(e):
                        logger.error(
                            f"Retry failed for {func.__name__}",
                            attempt=retry_state.attempt + 1,
                            max_attempts=config.max_retries + 1,
                            error=str(e),
                            total_delay=retry_state.total_delay
                        )
                        raise
                    
                    delay = retry_state.calculate_delay()
                    logger.warning(
                        f"Attempt failed for {func.__name__}",
                        attempt=retry_state.attempt + 1,
                        error=str(e),
                        delay=delay,
                        total_delay=retry_state.total_delay
                    )
                    
                    retry_state.next_attempt()
                    await asyncio.sleep(delay)
        
        return wrapper
    
    return decorator


async def retry_async(
    func: Callable[..., T],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """Retry function for async calls"""
    if config is None:
        config = RetryConfig()
    
    retry_state = RetryState(config)
    logger = get_logger(func.__module__)
    
    while True:
        try:
            if retry_state.attempt > 0:
                logger.info(
                    f"Retrying async call",
                    function=func.__name__,
                    attempt=retry_state.attempt + 1,
                    max_attempts=config.max_retries + 1,
                    total_delay=retry_state.total_delay
                )
            
            result = await func(*args, **kwargs)
            
            if retry_state.attempt > 0:
                logger.info(
                    f"Async retry successful",
                    function=func.__name__,
                    attempt=retry_state.attempt + 1,
                    total_delay=retry_state.total_delay
                )
            
            return result
            
        except Exception as e:
            retry_state.last_exception = e
            
            if not retry_state.should_retry(e):
                logger.error(
                    f"Async retry failed",
                    function=func.__name__,
                    attempt=retry_state.attempt + 1,
                    max_attempts=config.max_retries + 1,
                    error=str(e),
                    total_delay=retry_state.total_delay
                )
                raise
            
            delay = retry_state.calculate_delay()
            logger.warning(
                f"Async attempt failed",
                function=func.__name__,
                attempt=retry_state.attempt + 1,
                error=str(e),
                delay=delay,
                total_delay=retry_state.total_delay
            )
            
            retry_state.next_attempt()
            await asyncio.sleep(delay)


# Predefined retry configurations
DEFAULT_RETRY = RetryConfig(max_retries=3, base_delay=1.0)
AGGRESSIVE_RETRY = RetryConfig(max_retries=5, base_delay=0.5, backoff_multiplier=1.5)
CONSERVATIVE_RETRY = RetryConfig(max_retries=2, base_delay=2.0, backoff_multiplier=3.0)
NETWORK_RETRY = RetryConfig(
    max_retries=4,
    base_delay=0.1,
    max_delay=10.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    jitter=True
)

# Retry configurations for specific services
GEMINI_RETRY = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    jitter=True,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        aiohttp.ClientError,
    )
)

FIRESTORE_RETRY = RetryConfig(
    max_retries=5,
    base_delay=0.5,
    max_delay=10.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    jitter=True,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
    )
)

TWILIO_RETRY = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=20.0,
    strategy=RetryStrategy.LINEAR_BACKOFF,
    jitter=True,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
    )
)
