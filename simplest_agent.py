import os
import ast
import operator
import time
import logging
from functools import wraps
from datetime import datetime, timedelta
from typing import Optional, Any, Callable

from langchain_ollama import ChatOllama
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

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
                      circuit_breaker: Optional[CircuitBreaker] = None):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Check circuit breaker first
            if circuit_breaker and not circuit_breaker.is_available():
                raise Exception("Service temporarily unavailable (circuit breaker open)")
            
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
                    
                    # Record failure for circuit breaker
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                    
                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    # Log the retry attempt
                    logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f}s...")
                    time.sleep(delay)
            
            # All retries exhausted
            raise last_exception
        
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
        """Recursively evaluate AST nodes safely."""
        if isinstance(node, ast.Num):  # For older Python versions
            return node.n
        elif isinstance(node, ast.Constant):  # For newer Python versions
            return node.value
        elif isinstance(node, ast.BinOp):
            left = self._evaluate_node(node.left)
            right = self._evaluate_node(node.right)
            op = self.allowed_ops.get(type(node.op))
            if op is None:
                raise ValueError(f'Unsupported operation: {type(node.op).__name__}')
            
            # Special handling for division by zero
            if type(node.op) in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ValueError('Division by zero')
            
            # Prevent extremely large power operations (DoS protection)
            if type(node.op) == ast.Pow and abs(right) > 100:
                raise ValueError('Power operation too large')
            
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._evaluate_node(node.operand)
            op = self.allowed_ops.get(type(node.op))
            if op is None:
                raise ValueError(f'Unsupported unary operation: {type(node.op).__name__}')
            return op(operand)
        elif isinstance(node, ast.Expression):
            return self._evaluate_node(node.body)
        else:
            raise ValueError(f'Unsupported node type: {type(node).__name__}')
    
    def evaluate_expression(self, expression: str) -> float:
        """Safely evaluate a mathematical expression."""
        # Basic input validation
        if not isinstance(expression, str):
            raise ValueError('Expression must be a string')
        
        expression = expression.strip()
        if len(expression) == 0:
            raise ValueError('Expression cannot be empty')
        
        if len(expression) > 1000:  # Prevent extremely long expressions
            raise ValueError('Expression too long')
        
        # Check for potentially dangerous patterns
        dangerous_patterns = [
            '__', 'import', 'exec', 'eval', 'compile', 'open', 
            'file', 'input', 'raw_input', 'reload', 'vars', 'locals', 'globals'
        ]
        
        expression_lower = expression.lower()
        for pattern in dangerous_patterns:
            if pattern in expression_lower:
                raise ValueError(f'Potentially dangerous pattern detected: {pattern}')
        
        # Only allow mathematical characters and basic operations
        allowed_chars = set('0123456789+-*/%.() \t\n')
        if not all(c in allowed_chars for c in expression):
            raise ValueError('Expression contains invalid characters')
        
        try:
            # Parse the expression into an AST
            tree = ast.parse(expression, mode='eval')
            
            # Evaluate the AST safely
            result = self._evaluate_node(tree)
            
            return result
            
        except (SyntaxError, ValueError) as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f'Invalid expression: {str(e)}')
        except ZeroDivisionError:
            raise ValueError('Division by zero')
        except Exception as e:
            raise ValueError(f'Error evaluating expression: {str(e)}')


# ==========================================================
#   Custom Tool for Calculator
#
class CalculatorInput(BaseModel):
    expression: str = Field(description="Mathematical expression to evaluate")


class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Useful for when you need to answer questions about math"

    @retry_with_backoff(max_retries=2, base_delay=0.5)
    def _run(self, expression: str) -> str:
        """Use the tool to calculate mathematical expressions safely."""
        try:
            calculator = SafeCalculator()
            result = calculator.evaluate_expression(expression)
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"


# ==========================================================
#   Enhanced Agent with Retry Logic
# ==========================================================

class RobustAgent:
    """Enhanced agent wrapper with retry mechanisms and error handling."""
    
    def __init__(self, agent):
        self.agent = agent
        self.circuit_breaker = llm_circuit_breaker
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, circuit_breaker=llm_circuit_breaker)
    def _invoke_with_retry(self, input_data: dict) -> dict:
        """Invoke agent with retry logic and circuit breaker."""
        try:
            return self.agent.invoke(input_data)
        except Exception as e:
            logging.error(f"Agent invocation failed: {str(e)}")
            raise
    
    def invoke(self, input_data: dict) -> dict:
        """Public interface for agent invocation with comprehensive error handling."""
        try:
            return self._invoke_with_retry(input_data)
        except Exception as e:
            # Fallback response when all retries are exhausted
            if self.circuit_breaker.state == 'open':
                return {
                    "output": "I'm experiencing connectivity issues right now. Please try again in a moment. "
                             "In the meantime, you can use the calculator directly with simple expressions."
                }
            else:
                return {
                    "output": f"I encountered an error: {str(e)}. Please try rephrasing your question or "
                             "contact support if the issue persists."
                }
    
    def chat(self, message: str) -> str:
        """Convenient chat interface with error handling."""
        try:
            result = self.invoke({"input": message})
            return result.get("output", "No response generated")
        except Exception as e:
            return f"Error processing your message: {str(e)}"



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

@retry_with_backoff(max_retries=3, base_delay=2.0, circuit_breaker=llm_circuit_breaker)
def initialize_llm():
    """Initialize the language model with retry logic."""
    try:
        return ChatOllama(model="llama3.2:3b", temperature=0, provider="ollama")
    except Exception as e:
        logging.error(f"Failed to initialize LLM: {str(e)}")
        raise

# Initialize components with error handling
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
    
    logging.info("Agent initialized successfully with retry mechanisms")

except Exception as e:
    logging.error(f"Failed to initialize agent: {str(e)}")
    agent = None

# Run the agent only when script is executed directly
if __name__ == "__main__":
    if agent is None:
        print("Error: Agent failed to initialize. Please check your Ollama installation and try again.")
    else:
        try:
            print("🤖 Enhanced Agent with Retry Logic Initialized!")
            print("Circuit Breaker Status:", llm_circuit_breaker.state)
            print("=" * 50)
            
            # Test the enhanced agent with error handling
            response = agent.chat("Calculate 15% of 85.")
            print(f"Agent Response: {response}")
            
        except Exception as e:
            print(f"Error running agent: {str(e)}")
            print("The agent will continue to attempt retries as configured.")