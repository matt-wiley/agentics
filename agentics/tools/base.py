"""
Base classes and utilities for agentics tools.

This module provides foundation classes for building secure and robust tools
in the agentics framework.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict

from ..error_handling import AgentError, ErrorCategory


class BaseSecureTool(ABC):
    """Base class for secure tools with built-in validation and error handling."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data for security and correctness."""
        pass
    
    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Execute the tool's main functionality."""
        pass
    
    def run(self, input_data: Any, context: Optional[Dict] = None) -> Any:
        """Safe execution wrapper with validation and error handling."""
        try:
            # Validate input
            if not self.validate_input(input_data):
                raise AgentError(
                    f"Invalid input for {self.name} tool",
                    ErrorCategory.VALIDATION,
                    context={"tool": self.name, "input": str(input_data)[:100]}
                )
            
            # Execute with context
            return self.execute(input_data)
            
        except AgentError:
            raise  # Re-raise structured errors
        except Exception as e:
            # Wrap unexpected errors
            raise AgentError(
                f"Error in {self.name} tool: {str(e)}",
                ErrorCategory.UNKNOWN,
                context={
                    "tool": self.name,
                    "error_type": type(e).__name__,
                    "original_error": str(e)
                }
            )
