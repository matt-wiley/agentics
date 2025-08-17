"""
Safe mathematical expression evaluator and calculator tool.

This module provides a security-focused calculator that safely evaluates
mathematical expressions while preventing code injection attacks.
"""

import ast
import operator
import math
from typing import Union

from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from ..error_handling import AgentError, ErrorCategory, retry_with_backoff, error_handler


class SafeCalculator:
    """A safe mathematical expression evaluator that prevents code injection."""

    def __init__(self, max_expression_length: int = 1000, max_power: int = 100):
        self.max_expression_length = max_expression_length
        self.max_power = max_power
        
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
                if type(node.op) == ast.Pow and abs(right) > self.max_power:
                    raise AgentError(
                        'Power operation too large (security limit)',
                        ErrorCategory.SECURITY,
                        context={"base": left, "exponent": right, "limit": self.max_power}
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
            if len(expression) > self.max_expression_length:
                raise AgentError(
                    'Expression too long (security limit)',
                    ErrorCategory.SECURITY,
                    context={"expression_length": len(expression), "limit": self.max_expression_length}
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


class CalculatorInput(BaseModel):
    """Input model for calculator tool."""
    expression: str = Field(description="Mathematical expression to evaluate")


class CalculatorTool(BaseTool):
    """LangChain tool for safe mathematical calculations."""
    
    name: str = "calculator"
    description: str = "Useful for when you need to answer questions about math"

    def __init__(self, max_expression_length: int = None, max_power: int = None):
        super().__init__()
        
        # Store configuration values as private attributes to avoid Pydantic conflicts
        # Get config values if available
        try:
            from ..config import config
            self._max_expression_length = max_expression_length or config.calculator_max_expression_length
            self._max_power = max_power or config.calculator_max_power
        except ImportError:
            self._max_expression_length = max_expression_length or 1000
            self._max_power = max_power or 100

    @retry_with_backoff(max_retries=2, operation_name="calculator_tool", error_handler=error_handler)
    def _run(self, expression: str) -> str:
        """Use the tool to calculate mathematical expressions safely."""
        try:
            calculator = SafeCalculator(
                max_expression_length=self._max_expression_length,
                max_power=self._max_power
            )
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
