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

from langchain_ollama import ChatOllama
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

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
                      circuit_breaker: Optional[CircuitBreaker] = None, operation_name: str = "operation"):
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
                if type(node.op) == ast.Pow and abs(right) > 100:
                    raise AgentError(
                        'Power operation too large (security limit)',
                        ErrorCategory.SECURITY,
                        context={"base": left, "exponent": right, "limit": 100}
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
            if len(expression) > 1000:
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

    @retry_with_backoff(max_retries=2, base_delay=0.5, operation_name="calculator_tool")
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
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, circuit_breaker=llm_circuit_breaker, operation_name="agent_invoke")
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
#   Main Application with Enhanced Error Handling
# ==========================================================

# Configure logging for retry mechanisms
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Set your API key
os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_KEY", "")
os.environ["OPENAI_API_BASE"] = "http://127.0.0.1:4000"

@retry_with_backoff(max_retries=3, base_delay=2.0, circuit_breaker=llm_circuit_breaker, operation_name="llm_initialization")
def initialize_llm():
    """Initialize the language model with retry logic."""
    try:
        return ChatOllama(model="llama3.2:3b", temperature=0, provider="ollama")
    except Exception as e:
        # Add context about the initialization failure
        raise AgentError(
            f"Failed to initialize LLM: {str(e)}",
            ErrorCategory.CONFIGURATION,
            context={"model": "llama3.2:3b", "provider": "ollama", "error": str(e)}
        )

# Initialize components with comprehensive error handling
try:
    # Initialize the language model with retry
    llm = initialize_llm()
    
    # Load custom calculator tool
    calculator_tool = CalculatorTool()
    custom_tools = [calculator_tool]
    
    # Set up memory for conversation context
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    # Initialize the base agent
    base_agent = initialize_agent(
        custom_tools,
        llm,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        verbose=True
    )
    
    # Wrap with enhanced error handling
    agent = RobustAgent(base_agent)
    
    logging.info("Agent initialized successfully with comprehensive error handling")

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