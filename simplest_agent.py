import os
import ast
import operator

from langchain_ollama import ChatOllama
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# ==========================================================
#   Safe Mathematical Expression Evaluator
#
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

    def _run(self, expression: str) -> str:
        """Use the tool to calculate mathematical expressions safely."""
        try:
            calculator = SafeCalculator()
            result = calculator.evaluate_expression(expression)
            return str(result)
        except Exception as e:
            return f"Error: {str(e)}"



# ==========================================================
#   Main Code
#

# Set your API key
os.environ["OPENAI_API_KEY"] = os.getenv("LITELLM_KEY", "")
os.environ["OPENAI_API_BASE"] = "http://127.0.0.1:4000"

# Initialize the language model
llm = ChatOllama(model="llama3.2:3b", temperature=0, provider="ollama")

# Load custom calculator tool
calculator_tool = CalculatorTool()

custom_tools = [calculator_tool]

# Load tools the agent can use
# tools = load_tools(
#     tool_names=[],
#     llm=llm
# )

# Set up memory for conversation context
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Initialize the agent
agent = initialize_agent(
    custom_tools,
    llm,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,  # Agent type
    memory=memory,
    verbose=True  # Show the agent's thought process
)

# Run the agent only when script is executed directly
if __name__ == "__main__":
    agent.invoke({"input": "Calculate 15% of 85."})