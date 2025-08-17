"""
Error handling package for agentics.

Provides structured error handling, classification, and resilience patterns.
"""

from .exceptions import ErrorCategory, AgentError
from .handlers import ErrorHandler
from .resilience import CircuitBreaker, retry_with_backoff, create_retry_decorator_with_config

# Create default instances - use lazy loading to avoid circular dependencies
_error_handler = None
_llm_circuit_breaker = None

def get_error_handler():
    """Get or create the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

def get_llm_circuit_breaker():
    """Get or create the global LLM circuit breaker instance."""
    global _llm_circuit_breaker
    if _llm_circuit_breaker is None:
        # Import config only when needed to avoid circular dependency
        try:
            from ..config import config
            _llm_circuit_breaker = CircuitBreaker(
                failure_threshold=config.circuit_breaker_failure_threshold,
                timeout=config.circuit_breaker_timeout
            )
        except ImportError:
            # Fallback to default values if config is not available
            _llm_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
    return _llm_circuit_breaker

# For backward compatibility, provide these as properties
error_handler = get_error_handler()
llm_circuit_breaker = get_llm_circuit_breaker()

__all__ = [
    'ErrorCategory',
    'AgentError', 
    'ErrorHandler',
    'CircuitBreaker',
    'retry_with_backoff',
    'create_retry_decorator_with_config',
    'get_error_handler',
    'get_llm_circuit_breaker',
    'error_handler',
    'llm_circuit_breaker'
]
