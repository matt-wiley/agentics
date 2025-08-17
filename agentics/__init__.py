"""
Agentics - A security-focused LLM agent framework.

This package provides a modular, enterprise-grade framework for building
LLM agents with comprehensive error handling, monitoring, and security features.
"""

# Core configuration
from .config import AgentConfig, config

# Error handling and resilience
from .error_handling import (
    ErrorCategory,
    AgentError,
    ErrorHandler,
    CircuitBreaker,
    retry_with_backoff,
    error_handler,
    llm_circuit_breaker
)

# Tools
from .tools import (
    SafeCalculator,
    CalculatorTool,
    CalculatorInput,
    BaseSecureTool
)

__version__ = "0.1.0"
__all__ = [
    'AgentConfig',
    'config',
    'ErrorCategory',
    'AgentError',
    'ErrorHandler',
    'CircuitBreaker',
    'retry_with_backoff',
    'error_handler',
    'llm_circuit_breaker',
    'SafeCalculator',
    'CalculatorTool',
    'CalculatorInput',
    'BaseSecureTool'
]
