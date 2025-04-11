import os
from typing import Type
from langchain_ollama import ChatOllama
from langchain.agents import AgentType, initialize_agent
from langchain.memory import ConversationBufferMemory
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# ==========================================================
#   Custom Tool for Calculator
#
class CalculatorInput(BaseModel):
    expression: str = Field(description="Mathematical expression to evaluate")


class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Useful for performing mathematical calculations"
    args_schema: Type[BaseModel] = CalculatorInput
    
    def __init__(self):
        super().__init__()

    def _run(self, expression: str) -> str:
        try:
            return str(eval(expression))
        except Exception as e:
            return f"Error calculating result: {e}"
    
    def _arun(self, expression: str):
        # For async implementation
        raise NotImplementedError("Calculator does not support async")



# ==========================================================
#   Main Code
#

# Set your API key
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENAI_API_BASE"] = "http://127.0.0.1:11434"

# Initialize the language model
llm = ChatOllama(model="llama3.2:3b", temperature=0)

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

# Run the agent
agent.invoke({"input": "Calculate 15% of 85."})