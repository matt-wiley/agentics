"""
Centralized error handling with structured logging and context-aware responses.

This module provides the ErrorHandler class for classifying, logging, and 
tracking errors throughout the agent system.
"""

import logging
import traceback
from typing import Optional, Dict

from .exceptions import ErrorCategory, AgentError


class ErrorHandler:
    """Centralized error handling with structured logging and context-aware responses."""

    def __init__(self):
        self.logger = logging.getLogger("agent_error_handler")
        self.error_counts = {}  # Track error patterns

    def classify_error(self, error: Exception, context: Optional[Dict] = None) -> ErrorCategory:
        """Classify error based on type and context."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Network/connectivity errors
        if any(keyword in error_str for keyword in ['connection', 'network', 'timeout', 'refused', 'unreachable']):
            return ErrorCategory.CONNECTIVITY

        # Validation errors
        if any(keyword in error_str for keyword in ['invalid', 'malformed', 'syntax', 'format', 'parse']):
            return ErrorCategory.VALIDATION

        # Mathematical computation errors
        if any(keyword in error_str for keyword in ['division by zero', 'math domain', 'overflow', 'calculation']):
            return ErrorCategory.COMPUTATION

        # Security-related errors
        if any(keyword in error_str for keyword in ['dangerous', 'security', 'blocked', 'forbidden', 'injection']):
            return ErrorCategory.SECURITY

        # Timeout errors
        if 'timeout' in error_str or 'time out' in error_str:
            return ErrorCategory.TIMEOUT

        # Resource errors
        if any(keyword in error_str for keyword in ['memory', 'resource', 'limit', 'quota', 'capacity']):
            return ErrorCategory.RESOURCE

        # Configuration errors
        if any(keyword in error_str for keyword in ['config', 'environment', 'missing', 'not found']):
            return ErrorCategory.CONFIGURATION

        return ErrorCategory.UNKNOWN

    def handle_error(self, error: Exception, context: Optional[Dict] = None,
                    operation: str = "unknown") -> AgentError:
        """Handle error with classification, logging, and structured response."""

        # Classify the error
        category = self.classify_error(error, context)

        # Track error patterns
        error_key = f"{category.value}_{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Create structured error
        agent_error = AgentError(
            message=str(error),
            category=category,
            context={
                **(context or {}),
                "operation": operation,
                "error_type": type(error).__name__,
                "error_count": self.error_counts[error_key],
                "stack_trace": traceback.format_exc() if self.logger.isEnabledFor(logging.DEBUG) else None
            }
        )

        # Log the error with appropriate level
        log_level = self._get_log_level(category)
        self.logger.log(log_level,
                       f"[{agent_error.trace_id}] {operation} failed: {category.value} error - {str(error)}",
                       extra={"error_details": agent_error.to_dict()})

        return agent_error

    def _get_log_level(self, category: ErrorCategory) -> int:
        """Determine appropriate log level based on error category."""
        levels = {
            ErrorCategory.SECURITY: logging.ERROR,
            ErrorCategory.CONFIGURATION: logging.ERROR,
            ErrorCategory.CONNECTIVITY: logging.WARNING,
            ErrorCategory.TIMEOUT: logging.WARNING,
            ErrorCategory.RESOURCE: logging.WARNING,
            ErrorCategory.VALIDATION: logging.INFO,
            ErrorCategory.COMPUTATION: logging.INFO,
            ErrorCategory.UNKNOWN: logging.ERROR
        }
        return levels.get(category, logging.WARNING)

    def get_error_stats(self) -> Dict:
        """Get error statistics for monitoring."""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_breakdown": dict(self.error_counts),
            "most_common": max(self.error_counts.items(), key=lambda x: x[1]) if self.error_counts else None
        }
