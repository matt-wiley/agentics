import os
import ast
import operator
import time
import logging
import json
import math
import traceback
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Any, Callable, Dict, List, Union
from enum import Enum
from dataclasses import dataclass, field

from langchain_ollama import ChatOllama
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# ==========================================================
#   Configuration Management System
# ==========================================================

@dataclass
class AgentConfig:
    """Comprehensive configuration management for the agent."""

    # Model Configuration
    model_name: str = field(default_factory=lambda: os.getenv("AGENT_MODEL", "llama3.2:3b"))
    model_provider: str = field(default_factory=lambda: os.getenv("AGENT_PROVIDER", "ollama"))
    model_temperature: float = field(default_factory=lambda: float(os.getenv("AGENT_TEMPERATURE", "0.0")))

    # API Configuration
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_api_base: str = field(default_factory=lambda: os.getenv("OPENAI_API_BASE", ""))
    litellm_key: str = field(default_factory=lambda: os.getenv("LITELLM_KEY", ""))
    litellm_base_url: str = field(default_factory=lambda: os.getenv("LITELLM_BASE_URL", "http://127.0.0.1:4000"))

    # Agent Behavior Configuration
    agent_verbose: bool = field(default_factory=lambda: os.getenv("AGENT_VERBOSE", "true").lower() == "true")
    agent_max_iterations: int = field(default_factory=lambda: int(os.getenv("AGENT_MAX_ITERATIONS", "15")))
    agent_timeout: int = field(default_factory=lambda: int(os.getenv("AGENT_TIMEOUT", "300")))

    # Retry Configuration
    retry_max_attempts: int = field(default_factory=lambda: int(os.getenv("RETRY_MAX_ATTEMPTS", "3")))
    retry_base_delay: float = field(default_factory=lambda: float(os.getenv("RETRY_BASE_DELAY", "1.0")))
    retry_max_delay: float = field(default_factory=lambda: float(os.getenv("RETRY_MAX_DELAY", "60.0")))

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = field(default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")))
    circuit_breaker_timeout: int = field(default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60")))

    # Calculator Configuration
    calculator_max_expression_length: int = field(default_factory=lambda: int(os.getenv("CALCULATOR_MAX_LENGTH", "1000")))
    calculator_max_power: int = field(default_factory=lambda: int(os.getenv("CALCULATOR_MAX_POWER", "100")))

    # Logging Configuration
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_format: str = field(default_factory=lambda: os.getenv("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s"))

    # Memory Configuration
    memory_key: str = field(default_factory=lambda: os.getenv("MEMORY_KEY", "chat_history"))
    memory_return_messages: bool = field(default_factory=lambda: os.getenv("MEMORY_RETURN_MESSAGES", "true").lower() == "true")

    def validate(self) -> List[str]:
        """Validate configuration and return list of validation errors."""
        errors = []

        # Validate model configuration
        if not self.model_name:
            errors.append("AGENT_MODEL cannot be empty")

        if self.model_provider not in ["ollama", "openai", "litellm"]:
            errors.append(f"AGENT_PROVIDER must be one of: ollama, openai, litellm. Got: {self.model_provider}")

        if not (0.0 <= self.model_temperature <= 2.0):
            errors.append(f"AGENT_TEMPERATURE must be between 0.0 and 2.0. Got: {self.model_temperature}")

        # Validate API configuration based on provider
        if self.model_provider == "ollama" and not self.ollama_base_url:
            errors.append("OLLAMA_BASE_URL is required when using ollama provider")

        if self.model_provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required when using openai provider")

        if self.model_provider == "litellm" and not self.litellm_key:
            errors.append("LITELLM_KEY is required when using litellm provider")

        # Validate numeric ranges
        if self.agent_max_iterations < 1:
            errors.append(f"AGENT_MAX_ITERATIONS must be >= 1. Got: {self.agent_max_iterations}")

        if self.agent_timeout < 1:
            errors.append(f"AGENT_TIMEOUT must be >= 1. Got: {self.agent_timeout}")

        if self.retry_max_attempts < 1:
            errors.append(f"RETRY_MAX_ATTEMPTS must be >= 1. Got: {self.retry_max_attempts}")

        if self.retry_base_delay <= 0:
            errors.append(f"RETRY_BASE_DELAY must be > 0. Got: {self.retry_base_delay}")

        if self.retry_max_delay <= self.retry_base_delay:
            errors.append(f"RETRY_MAX_DELAY must be > RETRY_BASE_DELAY. Got: {self.retry_max_delay} <= {self.retry_base_delay}")

        if self.circuit_breaker_failure_threshold < 1:
            errors.append(f"CIRCUIT_BREAKER_FAILURE_THRESHOLD must be >= 1. Got: {self.circuit_breaker_failure_threshold}")

        if self.circuit_breaker_timeout < 1:
            errors.append(f"CIRCUIT_BREAKER_TIMEOUT must be >= 1. Got: {self.circuit_breaker_timeout}")

        if self.calculator_max_expression_length < 10:
            errors.append(f"CALCULATOR_MAX_LENGTH must be >= 10. Got: {self.calculator_max_expression_length}")

        if self.calculator_max_power < 1:
            errors.append(f"CALCULATOR_MAX_POWER must be >= 1. Got: {self.calculator_max_power}")

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of: {valid_log_levels}. Got: {self.log_level}")

        return errors

    def setup_environment(self) -> None:
        """Set up environment variables for compatibility with existing code."""
        # Set up OpenAI environment variables for LangChain compatibility
        if self.model_provider == "openai":
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
            if self.openai_api_base:
                os.environ["OPENAI_API_BASE"] = self.openai_api_base
        elif self.model_provider == "litellm":
            os.environ["OPENAI_API_KEY"] = self.litellm_key
            os.environ["OPENAI_API_BASE"] = self.litellm_base_url

        # Set up logging configuration
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format
        )

    def get_model_kwargs(self) -> Dict[str, Any]:
        """Get model initialization parameters based on provider."""
        base_kwargs = {
            "model": self.model_name,
            "temperature": self.model_temperature
        }

        if self.model_provider == "ollama":
            base_kwargs.update({
                "provider": "ollama",
                "base_url": self.ollama_base_url
            })

        return base_kwargs

    def __post_init__(self):
        """Validate configuration after initialization."""
        validation_errors = self.validate()
        if validation_errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in validation_errors)
            raise AgentError(
                error_message,
                ErrorCategory.CONFIGURATION,
                context={"validation_errors": validation_errors},
                user_message="The agent configuration has invalid settings. Please check your environment variables.",
                recovery_suggestions=[
                    "Review and correct the environment variables mentioned in the errors",
                    "Check the documentation for valid configuration values",
                    "Ensure all required environment variables are set for your chosen provider"
                ]
            )

        # Set up environment after successful validation
        self.setup_environment()


# Global configuration instance
config = AgentConfig()

# ==========================================================
#   Error Classification and Handling System
# ==========================================================

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


# Initialize global error handler
error_handler = ErrorHandler()

# ==========================================================
#   Retry Mechanisms and Circuit Breaker
# ==========================================================

class CircuitBreaker:
    """Simple circuit breaker for handling service failures."""

    def __init__(self, failure_threshold: int = None, timeout: int = None):
        # Use configuration defaults if not specified
        self.failure_threshold = failure_threshold or config.circuit_breaker_failure_threshold
        self.timeout = timeout or config.circuit_breaker_timeout
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


def retry_with_backoff(max_retries: int = None, base_delay: float = None, max_delay: float = None,
                      circuit_breaker: Optional[CircuitBreaker] = None, operation_name: str = "operation"):
    """Decorator for retry logic with exponential backoff and enhanced error handling."""
    # Use configuration defaults if not specified
    if max_retries is None:
        max_retries = config.retry_max_attempts
    if base_delay is None:
        base_delay = config.retry_base_delay
    if max_delay is None:
        max_delay = config.retry_max_delay

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

                    # Use error handler to classify and log
                    handled_error = error_handler.handle_error(
                        e,
                        context={"attempt": attempt + 1, "max_retries": max_retries + 1},
                        operation=operation_name
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

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)

                    # Log the retry attempt with context
                    logging.info(f"[{handled_error.trace_id}] Retrying {operation_name} in {delay:.2f}s "
                               f"(attempt {attempt + 2}/{max_retries + 1})")
                    time.sleep(delay)

            # All retries exhausted - create final error with context
            final_error = error_handler.handle_error(
                last_exception,
                context={"retries_exhausted": True, "total_attempts": max_retries + 1},
                operation=f"{operation_name}_final_failure"
            )
            raise final_error

        return wrapper
    return decorator


# Initialize circuit breaker for LLM operations
llm_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

# ==========================================================
#   Safe Mathematical Expression Evaluator
# ==========================================================

class SafeCalculator:
    """A safe mathematical expression evaluator that prevents code injection."""

    def __init__(self):
        # Define allowed operations mapping AST nodes to operator functions
        self.allowed_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

    def _evaluate_node(self, node):
        """Recursively evaluate AST nodes safely with enhanced error handling."""
        try:
            if isinstance(node, ast.Num):  # For older Python versions
                return node.n
            elif isinstance(node, ast.Constant):  # For newer Python versions
                return node.value
            elif isinstance(node, ast.BinOp):
                left = self._evaluate_node(node.left)
                right = self._evaluate_node(node.right)
                op = self.allowed_ops.get(type(node.op))
                if op is None:
                    raise AgentError(
                        f'Unsupported operation: {type(node.op).__name__}',
                        ErrorCategory.VALIDATION,
                        context={"operation": type(node.op).__name__}
                    )

                # Special handling for division by zero
                if type(node.op) in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                    raise AgentError(
                        'Division by zero',
                        ErrorCategory.COMPUTATION,
                        context={"left_operand": left, "operation": type(node.op).__name__}
                    )

                # Prevent extremely large power operations (DoS protection)
                if type(node.op) == ast.Pow and abs(right) > config.calculator_max_power:
                    raise AgentError(
                        'Power operation too large (security limit)',
                        ErrorCategory.SECURITY,
                        context={"base": left, "exponent": right, "limit": config.calculator_max_power}
                    )

                return op(left, right)

            elif isinstance(node, ast.UnaryOp):
                operand = self._evaluate_node(node.operand)
                op = self.allowed_ops.get(type(node.op))
                if op is None:
                    raise AgentError(
                        f'Unsupported unary operation: {type(node.op).__name__}',
                        ErrorCategory.VALIDATION,
                        context={"operation": type(node.op).__name__, "operand": operand}
                    )
                return op(operand)
            elif isinstance(node, ast.Expression):
                return self._evaluate_node(node.body)
            else:
                raise AgentError(
                    f'Unsupported node type: {type(node).__name__}',
                    ErrorCategory.VALIDATION,
                    context={"node_type": type(node).__name__}
                )
        except AgentError:
            raise  # Re-raise structured errors
        except Exception as e:
            # Wrap unexpected errors in AST evaluation
            raise AgentError(
                f'Error in AST evaluation: {str(e)}',
                ErrorCategory.COMPUTATION,
                context={"node_type": type(node).__name__, "original_error": str(e)}
            )

    def evaluate_expression(self, expression: str) -> Union[int, float]:
        """Safely evaluate mathematical expressions with enhanced error handling."""
        try:
            # Input validation
            if not isinstance(expression, str):
                raise AgentError(
                    'Expression must be a string',
                    ErrorCategory.VALIDATION,
                    context={"provided_type": type(expression).__name__}
                )

            if not expression.strip():
                raise AgentError(
                    'Expression cannot be empty',
                    ErrorCategory.VALIDATION,
                    context={"expression_length": len(expression)}
                )

            # Length validation (DoS protection)
            if len(expression) > config.calculator_max_expression_length:
                raise AgentError(
                    'Expression too long (security limit)',
                    ErrorCategory.SECURITY,
                    context={"expression_length": len(expression), "limit": config.calculator_max_expression_length}
                )
                raise AgentError(
                    'Expression too long for security',
                    ErrorCategory.SECURITY,
                    context={"expression_length": len(expression), "max_length": 1000}
                )

            # Security pattern detection
            dangerous_patterns = ['__', 'import', 'exec', 'eval', 'open', 'file', 'input', 'raw_input']
            for pattern in dangerous_patterns:
                if pattern in expression.lower():
                    raise AgentError(
                        f'Potentially dangerous pattern detected: {pattern}',
                        ErrorCategory.SECURITY,
                        context={"detected_pattern": pattern, "expression": expression[:100]}
                    )

            # Character validation
            allowed_chars = set('0123456789+-*/%.() \t\n')
            invalid_chars = set(expression) - allowed_chars
            if invalid_chars:
                raise AgentError(
                    f'Invalid characters in expression: {", ".join(sorted(invalid_chars))}',
                    ErrorCategory.VALIDATION,
                    context={"invalid_chars": list(invalid_chars), "allowed_chars": list(allowed_chars)}
                )

            # Parse and evaluate
            try:
                tree = ast.parse(expression, mode='eval')
                result = self._evaluate_node(tree.body)

                # Validate result
                if not isinstance(result, (int, float)):
                    raise AgentError(
                        f'Invalid result type: {type(result)}',
                        ErrorCategory.COMPUTATION,
                        context={"result_type": type(result).__name__}
                    )

                # Check for infinite or NaN results
                if isinstance(result, float) and (not math.isfinite(result)):
                    raise AgentError(
                        'Result is infinite or not a number',
                        ErrorCategory.COMPUTATION,
                        context={"result": str(result)}
                    )

                return result

            except (SyntaxError, ValueError) as e:
                if isinstance(e, ValueError):
                    raise  # Re-raise AgentError instances
                raise AgentError(
                    f'Invalid mathematical expression: {str(e)}',
                    ErrorCategory.VALIDATION,
                    context={"syntax_error": str(e), "expression": expression}
                )

        except AgentError:
            raise  # Re-raise our structured errors
        except Exception as e:
            # Wrap unexpected errors
            raise AgentError(
                f'Unexpected error evaluating expression: {str(e)}',
                ErrorCategory.UNKNOWN,
                context={"original_error": str(e), "error_type": type(e).__name__}
            )


# ==========================================================
#   Custom Tool for Calculator
#
class CalculatorInput(BaseModel):
    expression: str = Field(description="Mathematical expression to evaluate")


class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Useful for when you need to answer questions about math"

    @retry_with_backoff(max_retries=2, operation_name="calculator_tool")
    def _run(self, expression: str) -> str:
        """Use the tool to calculate mathematical expressions safely."""
        try:
            calculator = SafeCalculator()
            result = calculator.evaluate_expression(expression)
            return str(result)
        except AgentError as e:
            # Return user-friendly message for structured errors
            return f"Calculator Error: {e.user_message}\n\nSuggestions:\n" + \
                   "\n".join(f"• {suggestion}" for suggestion in e.recovery_suggestions[:2])
        except Exception as e:
            # Handle any unexpected errors
            handled_error = error_handler.handle_error(e, operation="calculator_tool")
            return f"Calculator Error: {handled_error.user_message}"


# ==========================================================
#   Enhanced Agent with Retry Logic
# ==========================================================

class RobustAgent:
    """Enhanced agent wrapper with retry mechanisms and comprehensive error handling."""

    def __init__(self, agent):
        self.agent = agent
        self.circuit_breaker = llm_circuit_breaker
        self.error_handler = error_handler

    @retry_with_backoff(circuit_breaker=llm_circuit_breaker, operation_name="agent_invoke")
    def _invoke_with_retry(self, input_data: dict) -> dict:
        """Invoke agent with retry logic and circuit breaker."""
        try:
            return self.agent.invoke(input_data)
        except Exception as e:
            # Let the retry decorator handle classification and logging
            raise

    def invoke(self, input_data: dict) -> dict:
        """Public interface for agent invocation with comprehensive error handling."""
        try:
            return self._invoke_with_retry(input_data)
        except AgentError as e:
            # Handle structured errors from our system
            if e.category == ErrorCategory.CONNECTIVITY:
                return {
                    "output": f"{e.user_message}\n\n" + \
                             "While I'm having connectivity issues, you can still use basic calculator functions directly. " + \
                             "Try simple expressions like '2 + 3 * 4' or '(15 + 5) / 2'."
                }
            else:
                suggestions = "\n".join(f"• {s}" for s in e.recovery_suggestions[:3])
                return {
                    "output": f"{e.user_message}\n\nHere's what you can try:\n{suggestions}"
                }
        except Exception as e:
            # Handle any unexpected errors not caught by our system
            handled_error = self.error_handler.handle_error(e, operation="agent_invoke_fallback")
            return {
                "output": f"{handled_error.user_message}\n\nSuggestions:\n" + \
                         "\n".join(f"• {s}" for s in handled_error.recovery_suggestions[:2])
            }

    def chat(self, message: str) -> str:
        """Convenient chat interface with enhanced error handling."""
        try:
            if not message or not message.strip():
                return "Please provide a question or calculation for me to help with."

            # Add context for better error handling
            context = {"user_message": message[:100], "message_length": len(message)}

            result = self.invoke({"input": message})
            response = result.get("output", "No response generated")

            # Log successful interactions for monitoring
            logging.info(f"Successful interaction completed", extra={
                "message_length": len(message),
                "response_length": len(response),
                "circuit_breaker_state": self.circuit_breaker.state
            })

            return response

        except Exception as e:
            # Final safety net for chat interface
            handled_error = self.error_handler.handle_error(
                e,
                context={"user_message": message[:100]},
                operation="chat_interface"
            )
            return f"{handled_error.user_message}\n\nIf this problem continues, please try:\n" + \
                   "\n".join(f"• {s}" for s in handled_error.recovery_suggestions[:2])


# ==========================================================
#   ReAct Pattern Agent Implementation
# ==========================================================

class SimpleReActAgent:
    """Direct ReAct pattern implementation replacing deprecated LangChain initialize_agent."""

    def __init__(self, llm, tools, memory, config):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.memory = memory
        self.config = config
        self.max_iterations = config.agent_max_iterations

    def _format_tools(self) -> str:
        """Format tools description for ReAct prompt."""
        tool_descriptions = []
        for tool_name, tool in self.tools.items():
            tool_descriptions.append(f"{tool_name}: {tool.description}")
        return "\n".join(tool_descriptions)

    def _get_react_prompt(self, user_input: str) -> str:
        """Create ReAct-style prompt with tools and conversation history."""
        tools_desc = self._format_tools()

        # Get conversation history from memory
        memory_context = ""
        if hasattr(self.memory, 'chat_memory') and self.memory.chat_memory.messages:
            memory_context = "\nConversation History:\n"
            for msg in self.memory.chat_memory.messages[-6:]:  # Last 6 messages for context
                if hasattr(msg, 'content'):
                    role = "Human" if msg.type == "human" else "Assistant"
                    memory_context += f"{role}: {msg.content}\n"

        prompt = f"""You are a helpful assistant that can use tools to answer questions. You have access to the following tools:

{tools_desc}

When using the calculator tool:
- For percentages: convert to decimal form (e.g., 15% of 85 becomes 0.15 * 85)
- Use proper mathematical expressions (e.g., 2 + 3, 10 / 2, 5 * 6)
- Include parentheses for complex expressions (e.g., (15 + 5) * 2)

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{', '.join(self.tools.keys())}]
Action Input: the input to the action (for calculator: use a mathematical expression)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

{memory_context}

Question: {user_input}
Thought:"""

        return prompt

    def _extract_action(self, text: str) -> tuple[str, str]:
        """Extract action and action input from LLM response."""
        try:
            # Look for Action: and Action Input: patterns
            lines = text.strip().split('\n')
            action = None
            action_input = None

            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith('Action:'):
                    action = line[7:].strip()
                elif line.startswith('Action Input:'):
                    action_input = line[13:].strip()

            return action, action_input
        except Exception:
            return None, None

    def _should_stop(self, text: str) -> bool:
        """Check if the agent should stop (has final answer)."""
        return "Final Answer:" in text

    def _extract_final_answer(self, text: str) -> str:
        """Extract final answer from LLM response."""
        try:
            if "Final Answer:" in text:
                return text.split("Final Answer:")[-1].strip()
            return text.strip()
        except Exception:
            return text.strip()

    def invoke(self, input_data: dict) -> dict:
        """Main ReAct loop implementation."""
        try:
            user_input = input_data.get("input", "")
            if not user_input:
                return {"output": "Please provide a question or request."}

            # Store user input in memory
            self.memory.chat_memory.add_user_message(user_input)

            # Initialize ReAct loop
            current_prompt = self._get_react_prompt(user_input)
            iteration = 0

            while iteration < self.max_iterations:
                iteration += 1

                # Get LLM response
                try:
                    if hasattr(self.llm, 'invoke'):
                        response = self.llm.invoke(current_prompt)
                        if hasattr(response, 'content'):
                            llm_output = response.content
                        else:
                            llm_output = str(response)
                    else:
                        # Fallback for different LLM interfaces
                        llm_output = str(self.llm(current_prompt))

                except Exception as e:
                    error_msg = f"LLM call failed: {str(e)}"
                    logging.warning(error_msg)
                    return {"output": f"I encountered an issue processing your request: {error_msg}"}

                if self.config.agent_verbose:
                    print(f"\n--- Iteration {iteration} ---")
                    print(f"LLM Output: {llm_output}")

                # Check if we should stop
                if self._should_stop(llm_output):
                    final_answer = self._extract_final_answer(llm_output)
                    self.memory.chat_memory.add_ai_message(final_answer)
                    return {"output": final_answer}

                # Extract action and action input
                action, action_input = self._extract_action(llm_output)

                if not action or action not in self.tools:
                    # If no valid action, ask LLM to clarify
                    current_prompt += f" {llm_output}\nPlease specify a valid action from: {', '.join(self.tools.keys())}\nThought:"
                    continue

                # Execute tool
                try:
                    tool = self.tools[action]
                    observation = tool._run(action_input)

                    if self.config.agent_verbose:
                        print(f"Action: {action}")
                        print(f"Action Input: {action_input}")
                        print(f"Observation: {observation}")

                    # Continue the conversation with observation
                    current_prompt += f" {llm_output}\nObservation: {observation}\nThought:"

                except Exception as e:
                    observation = f"Error using {action}: {str(e)}"
                    current_prompt += f" {llm_output}\nObservation: {observation}\nThought:"

            # Max iterations reached
            final_response = f"I've reached the maximum number of iterations ({self.max_iterations}) while working on your request. " + \
                           "Based on what I've discovered, I may need you to rephrase your question or break it down into smaller parts."

            self.memory.chat_memory.add_ai_message(final_response)
            return {"output": final_response}

        except Exception as e:
            error_msg = f"Error in ReAct agent: {str(e)}"
            logging.error(error_msg)
            return {"output": f"I encountered an unexpected error: {error_msg}"}


# ==========================================================
#   Main Application with Enhanced Error Handling
# ==========================================================

# Configuration-based initialization (logging already set up in config)

@retry_with_backoff(circuit_breaker=llm_circuit_breaker, operation_name="llm_initialization")
def initialize_llm():
    """Initialize the language model with retry logic and configuration-based settings."""
    try:
        model_kwargs = config.get_model_kwargs()
        return ChatOllama(**model_kwargs)
    except Exception as e:
        # Add context about the initialization failure
        raise AgentError(
            f"Failed to initialize LLM: {str(e)}",
            ErrorCategory.CONFIGURATION,
            context={
                "model": config.model_name,
                "provider": config.model_provider,
                "error": str(e),
                "model_kwargs": config.get_model_kwargs()
            }
        )

# Initialize components with comprehensive error handling
try:
    # Initialize the language model with retry
    llm = initialize_llm()

    # Load custom calculator tool
    calculator_tool = CalculatorTool()
    custom_tools = [calculator_tool]

    # Set up memory for conversation context using configuration
    memory = ConversationBufferMemory(
        memory_key=config.memory_key,
        return_messages=config.memory_return_messages
    )

    # Initialize the ReAct agent with configuration-based settings
    base_agent = SimpleReActAgent(
        llm=llm,
        tools=custom_tools,
        memory=memory,
        config=config
    )

    # Wrap with enhanced error handling
    agent = RobustAgent(base_agent)

    logging.info("ReAct agent initialized successfully with comprehensive error handling")

except AgentError as e:
    logging.error(f"Structured error during initialization: {e.user_message}")
    agent = None
except Exception as e:
    handled_error = error_handler.handle_error(e, operation="agent_initialization")
    logging.error(f"Failed to initialize agent: {handled_error.user_message}")
    agent = None

# Run the agent only when script is executed directly
if __name__ == "__main__":
    if agent is None:
        print("Error: Agent failed to initialize. Please check your Ollama installation and try again.")
        print("Error Statistics:", error_handler.get_error_stats())
    else:
        try:
            print("🤖 Enhanced Agent with Comprehensive Error Handling Initialized!")
            print("Circuit Breaker Status:", llm_circuit_breaker.state)
            print("=" * 50)

            # Test the enhanced agent with error handling
            response = agent.chat("Calculate 15% of 85.")
            print(f"Agent Response: {response}")

            print("\n" + "=" * 50)
            print("Error Handler Statistics:", error_handler.get_error_stats())

        except Exception as e:
            handled_error = error_handler.handle_error(e, operation="main_execution")
            print(f"Error running agent: {handled_error.user_message}")
            print("The agent will continue to attempt retries as configured.")