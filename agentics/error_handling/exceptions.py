"""
Error categories and custom exceptions for the agentics package.

This module provides the foundation for structured error handling throughout
the agent system, with rich context and recovery suggestions.
"""

import time
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class ErrorCategory(Enum):
    """Classification of error types for appropriate handling."""
    CONNECTIVITY = "connectivity"
    VALIDATION = "validation"
    COMPUTATION = "computation"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


class AgentError(Exception):
    """Base exception class for agent-related errors with rich context."""

    def __init__(self, message: str, category: ErrorCategory, context: Optional[Dict] = None,
                 user_message: Optional[str] = None, recovery_suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.context = context or {}
        self.user_message = user_message or self._generate_user_message()
        self.recovery_suggestions = recovery_suggestions or self._generate_recovery_suggestions()
        self.timestamp = datetime.now()
        self.trace_id = f"{int(time.time() * 1000)}"

    def _generate_user_message(self) -> str:
        """Generate user-friendly message based on error category."""
        messages = {
            ErrorCategory.CONNECTIVITY: "I'm having trouble connecting to the AI service. This is usually temporary.",
            ErrorCategory.VALIDATION: "There seems to be an issue with the input provided. Please check and try again.",
            ErrorCategory.COMPUTATION: "I encountered an error while processing your calculation.",
            ErrorCategory.CONFIGURATION: "There's a configuration issue that needs to be resolved.",
            ErrorCategory.SECURITY: "I blocked this request for security reasons.",
            ErrorCategory.TIMEOUT: "The operation is taking longer than expected. Please try a simpler request.",
            ErrorCategory.RESOURCE: "System resources are currently limited. Please try again shortly.",
            ErrorCategory.UNKNOWN: "I encountered an unexpected issue."
        }
        return messages.get(self.category, "An error occurred while processing your request.")

    def _generate_recovery_suggestions(self) -> List[str]:
        """Generate context-aware recovery suggestions."""
        suggestions = {
            ErrorCategory.CONNECTIVITY: [
                "Wait a moment and try again",
                "Check if your internet connection is stable",
                "Try using the calculator tool directly with simple math expressions"
            ],
            ErrorCategory.VALIDATION: [
                "Double-check your input for typos or formatting issues",
                "Try rephrasing your question",
                "Use simpler mathematical expressions"
            ],
            ErrorCategory.COMPUTATION: [
                "Try breaking your calculation into smaller parts",
                "Verify the mathematical expression is valid",
                "Use parentheses to clarify operation order"
            ],
            ErrorCategory.CONFIGURATION: [
                "Contact your system administrator",
                "Check if required services are running",
                "Verify environment variables are set correctly"
            ],
            ErrorCategory.SECURITY: [
                "Review your input for potentially dangerous content",
                "Stick to mathematical expressions and simple questions",
                "Avoid using system commands or code snippets"
            ],
            ErrorCategory.TIMEOUT: [
                "Try a simpler version of your request",
                "Break complex problems into smaller parts",
                "Wait a moment before retrying"
            ],
            ErrorCategory.RESOURCE: [
                "Wait a few moments and try again",
                "Try a simpler request that requires fewer resources",
                "Contact support if the issue persists"
            ],
            ErrorCategory.UNKNOWN: [
                "Try rephrasing your request",
                "Wait a moment and try again",
                "Contact support with the error details if the problem persists"
            ]
        }
        return suggestions.get(self.category, ["Try again or contact support if the issue persists"])

    def to_dict(self) -> Dict:
        """Convert error to structured dictionary for logging."""
        return {
            "error_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "message": self.message,
            "user_message": self.user_message,
            "recovery_suggestions": self.recovery_suggestions,
            "context": self.context
        }
