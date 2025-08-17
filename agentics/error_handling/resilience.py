"""
Retry mechanisms and circuit breaker patterns for resilient operations.

This module provides circuit breaker and retry decorators with exponential backoff
for handling service failures gracefully.
"""

import time
import logging
import random
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Callable, Any

from .exceptions import AgentError, ErrorCategory


class CircuitBreaker:
    """Simple circuit breaker for handling service failures."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'closed'  # closed, open, half-open

    def is_available(self) -> bool:
        """Check if the service is available."""
        if self.state == 'closed':
            return True
        elif self.state == 'open':
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = 'half-open'
                return True
            return False
        else:  # half-open
            return True

    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        self.state = 'closed'
        self.last_failure_time = None

    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0,
                      circuit_breaker: Optional[CircuitBreaker] = None, operation_name: str = "operation",
                      error_handler=None):
    """Decorator for retry logic with exponential backoff and enhanced error handling."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Check circuit breaker first
            if circuit_breaker and not circuit_breaker.is_available():
                error = AgentError(
                    "Service temporarily unavailable (circuit breaker open)",
                    ErrorCategory.CONNECTIVITY,
                    context={"circuit_breaker_state": circuit_breaker.state, "operation": operation_name}
                )
                raise error

            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    # Record success if circuit breaker is present
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    return result

                except Exception as e:
                    last_exception = e

                    # Use error handler if provided, otherwise create basic AgentError
                    if error_handler:
                        handled_error = error_handler.handle_error(
                            e,
                            context={"attempt": attempt + 1, "max_retries": max_retries + 1},
                            operation=operation_name
                        )
                    else:
                        # Fallback error handling without error_handler dependency
                        handled_error = AgentError(
                            str(e),
                            ErrorCategory.UNKNOWN,
                            context={"attempt": attempt + 1, "max_retries": max_retries + 1, "operation": operation_name}
                        )

                    # Record failure for circuit breaker
                    if circuit_breaker:
                        circuit_breaker.record_failure()

                    # Don't retry on certain error types
                    if handled_error.category in [ErrorCategory.SECURITY, ErrorCategory.VALIDATION]:
                        raise handled_error

                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        break

                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    # Add jitter to prevent thundering herd
                    delay = delay * (0.5 + random.random() * 0.5)

                    # Log the retry attempt with context
                    logging.info(f"[{handled_error.trace_id if hasattr(handled_error, 'trace_id') else 'unknown'}] "
                               f"Retrying {operation_name} in {delay:.2f}s "
                               f"(attempt {attempt + 2}/{max_retries + 1})")
                    time.sleep(delay)

            # All retries exhausted - create final error with context
            if error_handler:
                final_error = error_handler.handle_error(
                    last_exception,
                    context={"retries_exhausted": True, "total_attempts": max_retries + 1},
                    operation=f"{operation_name}_final_failure"
                )
            else:
                # Fallback without error_handler
                final_error = AgentError(
                    f"Operation {operation_name} failed after {max_retries + 1} attempts: {str(last_exception)}",
                    ErrorCategory.CONNECTIVITY,
                    context={"retries_exhausted": True, "total_attempts": max_retries + 1}
                )
            raise final_error

        return wrapper
    return decorator


def create_retry_decorator_with_config(config_getter=None, error_handler=None, circuit_breaker=None, operation_name="operation"):
    """Create a retry decorator using configuration values."""
    def get_config_values():
        if config_getter:
            try:
                config = config_getter()
                return (
                    config.retry_max_attempts,
                    config.retry_base_delay,
                    config.retry_max_delay
                )
            except Exception:
                pass
        # Fallback defaults
        return 3, 1.0, 60.0
    
    max_retries, base_delay, max_delay = get_config_values()
    return retry_with_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        circuit_breaker=circuit_breaker,
        operation_name=operation_name,
        error_handler=error_handler
    )
