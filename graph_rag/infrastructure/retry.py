"""Robust retry mechanisms with exponential backoff and circuit breaker patterns."""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Optional, Type, Union, List
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class RetryError(Exception):
    """Exception raised when retry attempts are exhausted."""
    
    def __init__(self, message: str, attempts: int, last_exception: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, message: str, circuit_state: CircuitState, failure_count: int):
        super().__init__(message)
        self.circuit_state = circuit_state
        self.failure_count = failure_count


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        non_retryable_exceptions: Optional[List[Type[Exception]]] = None,
        timeout: Optional[float] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or []
        self.non_retryable_exceptions = non_retryable_exceptions or []
        self.timeout = timeout
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an exception should trigger a retry."""
        if attempt >= self.max_attempts:
            return False
            
        # Check non-retryable exceptions first
        if self.non_retryable_exceptions:
            for exc_type in self.non_retryable_exceptions:
                if isinstance(exception, exc_type):
                    return False
        
        # If retryable exceptions are specified, only retry those
        if self.retryable_exceptions:
            for exc_type in self.retryable_exceptions:
                if isinstance(exception, exc_type):
                    return True
            return False
        
        # Default: retry most exceptions except critical ones
        non_retryable = (KeyboardInterrupt, SystemExit, MemoryError)
        return not isinstance(exception, non_retryable)
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay before next retry attempt."""
        import random
        
        delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add ±25% jitter to avoid thundering herd
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED
        
    def is_call_allowed(self) -> bool:
        """Check if a call is allowed through the circuit breaker."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker transitioning to {CircuitState.HALF_OPEN}")
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info(f"Circuit breaker transitioning to {CircuitState.CLOSED}")
    
    def record_failure(self, exception: Exception):
        """Record a failed call."""
        if not isinstance(exception, self.expected_exception):
            return
            
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker transitioning to {CircuitState.OPEN}")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker opening after {self.failure_count} failures"
            )


def retry_with_config(config: RetryConfig):
    """Decorator for retrying functions with custom configuration."""
    
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await _retry_async(func, config, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return _retry_sync(func, config, *args, **kwargs)
            return sync_wrapper
    
    return decorator


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    non_retryable_exceptions: Optional[List[Type[Exception]]] = None,
    timeout: Optional[float] = None
):
    """Simple retry decorator with common parameters."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        non_retryable_exceptions=non_retryable_exceptions,
        timeout=timeout
    )
    return retry_with_config(config)


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
):
    """Decorator for circuit breaker pattern."""
    
    breaker = CircuitBreaker(failure_threshold, recovery_timeout, expected_exception)
    
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not breaker.is_call_allowed():
                    raise CircuitBreakerError(
                        f"Circuit breaker is {breaker.state.value}",
                        breaker.state,
                        breaker.failure_count
                    )
                
                try:
                    result = await func(*args, **kwargs)
                    breaker.record_success()
                    return result
                except Exception as e:
                    breaker.record_failure(e)
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not breaker.is_call_allowed():
                    raise CircuitBreakerError(
                        f"Circuit breaker is {breaker.state.value}",
                        breaker.state,
                        breaker.failure_count
                    )
                
                try:
                    result = func(*args, **kwargs)
                    breaker.record_success()
                    return result
                except Exception as e:
                    breaker.record_failure(e)
                    raise
            return sync_wrapper
    
    return decorator


async def _retry_async(
    func: Callable, 
    config: RetryConfig, 
    *args, 
    **kwargs
) -> Any:
    """Execute async function with retry logic."""
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            if config.timeout:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=config.timeout
                )
            else:
                result = await func(*args, **kwargs)
            
            if attempt > 1:
                logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")
            
            return result
            
        except Exception as e:
            last_exception = e
            
            if not config.should_retry(e, attempt):
                logger.warning(
                    f"Function {func.__name__} failed on attempt {attempt}, "
                    f"not retrying: {e}"
                )
                raise
            
            if attempt < config.max_attempts:
                delay = config.get_delay(attempt)
                logger.warning(
                    f"Function {func.__name__} failed on attempt {attempt}/{config.max_attempts}, "
                    f"retrying in {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)
    
    # All attempts exhausted
    raise RetryError(
        f"Function {func.__name__} failed after {config.max_attempts} attempts",
        config.max_attempts,
        last_exception
    )


def _retry_sync(
    func: Callable,
    config: RetryConfig,
    *args,
    **kwargs
) -> Any:
    """Execute sync function with retry logic."""
    import time
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            
            if attempt > 1:
                logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")
            
            return result
            
        except Exception as e:
            last_exception = e
            
            if not config.should_retry(e, attempt):
                logger.warning(
                    f"Function {func.__name__} failed on attempt {attempt}, "
                    f"not retrying: {e}"
                )
                raise
            
            if attempt < config.max_attempts:
                delay = config.get_delay(attempt)
                logger.warning(
                    f"Function {func.__name__} failed on attempt {attempt}/{config.max_attempts}, "
                    f"retrying in {delay:.2f}s: {e}"
                )
                time.sleep(delay)
    
    # All attempts exhausted
    raise RetryError(
        f"Function {func.__name__} failed after {config.max_attempts} attempts",
        config.max_attempts,
        last_exception
    )


# Pre-configured retry decorators for common scenarios
database_retry = retry(
    max_attempts=3,
    base_delay=0.5,
    max_delay=5.0,
    retryable_exceptions=[ConnectionError, TimeoutError],
    non_retryable_exceptions=[ValueError, KeyError]
)

api_retry = retry(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    timeout=30.0
)

llm_retry = retry(
    max_attempts=3,
    base_delay=2.0,
    max_delay=10.0,
    exponential_base=1.5
)