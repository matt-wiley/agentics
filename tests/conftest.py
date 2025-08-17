"""Shared pytest fixtures for agentics tests."""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

# Import components from simplest_agent (before modularization)
from simplest_agent import (
    AgentConfig,
    SafeCalculator,
    ErrorHandler,
    CircuitBreaker,
    CalculatorTool,
    HealthChecker,
    ErrorCategory,
    AgentError
)


@pytest.fixture
def agent_config():
    """Provide test configuration with clean environment variables."""
    with patch.dict(os.environ, {
        'AGENT_MODEL': 'test-model',
        'AGENT_PROVIDER': 'ollama',
        'AGENT_TEMPERATURE': '0.0',
        'AGENT_VERBOSE': 'false',
        'OLLAMA_BASE_URL': 'http://localhost:11434',
        'LOG_LEVEL': 'WARNING'  # Reduce logging during tests
    }, clear=False):
        return AgentConfig()


@pytest.fixture
def test_env():
    """Provide clean test environment variables."""
    return {
        'AGENT_MODEL': 'test-model',
        'AGENT_PROVIDER': 'ollama',
        'AGENT_TEMPERATURE': '0.0',
        'AGENT_VERBOSE': 'false',
        'AGENT_MAX_ITERATIONS': '5',
        'OLLAMA_BASE_URL': 'http://localhost:11434',
        'LOG_LEVEL': 'WARNING',
        'RETRY_MAX_ATTEMPTS': '2',
        'CIRCUIT_BREAKER_FAILURE_THRESHOLD': '3'
    }


@pytest.fixture
def mock_llm():
    """Mock LLM for testing without external dependencies."""
    mock = Mock()
    mock.invoke.return_value.content = "Test response"
    mock.predict.return_value = "Test prediction"
    return mock


@pytest.fixture
def mock_langchain_components():
    """Mock LangChain components to avoid external dependencies."""
    with patch('langchain_ollama.ChatOllama') as mock_chat_ollama, \
         patch('langchain.memory.ConversationBufferMemory') as mock_memory, \
         patch('langchain.agents.initialize_agent') as mock_init_agent, \
         patch('langchain.agents.AgentType') as mock_agent_type:
        
        mock_chat_ollama.return_value.invoke.return_value.content = "Test response"
        mock_memory.return_value.chat_memory.messages = []
        mock_init_agent.return_value.run.return_value = "Test agent response"
        mock_agent_type.CHAT_CONVERSATIONAL_REACT_DESCRIPTION = "mock_type"
        
        yield {
            'chat_ollama': mock_chat_ollama,
            'memory': mock_memory,
            'init_agent': mock_init_agent,
            'agent_type': mock_agent_type
        }


@pytest.fixture
def calculator():
    """Provide SafeCalculator instance."""
    return SafeCalculator()


@pytest.fixture
def calculator_tool():
    """Provide CalculatorTool instance."""
    return CalculatorTool()


@pytest.fixture
def error_handler():
    """Provide ErrorHandler instance."""
    return ErrorHandler()


@pytest.fixture
def circuit_breaker():
    """Provide CircuitBreaker instance with test configuration."""
    return CircuitBreaker(failure_threshold=3, timeout=5)


@pytest.fixture
def health_checker(error_handler, circuit_breaker, calculator_tool):
    """Provide HealthChecker instance with all dependencies."""
    return HealthChecker(
        llm=None,  # Will be mocked in individual tests
        tools=[calculator_tool],
        circuit_breaker=circuit_breaker,
        error_handler=error_handler
    )


@pytest.fixture
def sample_expressions():
    """Provide sample mathematical expressions for testing."""
    return {
        'valid': [
            '2 + 2',
            '10 - 3',
            '5 * 6',
            '12 / 4',
            '2 ** 3',
            '(1 + 2) * 3',
            'abs(-5)',
            'max(1, 2, 3)',
            'min(1, 2, 3)',
            'round(3.14159, 2)'
        ],
        'security_threats': [
            '__import__("os")',
            'exec("print(1)")',
            'eval("2+2")',
            'open("/etc/passwd")',
            'subprocess.call("ls")',
            '__builtins__',
            'dir()',
            'vars()',
            'globals()',
            'locals()'
        ],
        'invalid': [
            '2 + abc',
            'undefined_function()',
            '2 +',
            '* 3',
            '((2 + 3)',
            '2 + 3))'
        ]
    }


@pytest.fixture
def error_test_cases():
    """Provide comprehensive error test cases."""
    return {
        ErrorCategory.SECURITY: {
            'input': '__import__("os")',
            'expected_pattern': 'security reasons'
        },
        ErrorCategory.VALIDATION: {
            'input': '2 + invalid_var',
            'expected_pattern': 'invalid characters'
        },
        ErrorCategory.COMPUTATION: {
            'input': '1 / 0',
            'expected_pattern': 'division by zero'
        },
        ErrorCategory.NETWORK: {
            'description': 'Network connectivity issues',
            'expected_pattern': 'network'
        }
    }


@contextmanager
def mock_time_sleep():
    """Mock time.sleep to speed up tests with delays."""
    with patch('time.sleep'):
        yield


@pytest.fixture
def mock_sleep():
    """Provide mock_time_sleep context manager as a fixture."""
    return mock_time_sleep


@pytest.fixture(autouse=True)
def setup_logging():
    """Automatically configure logging for tests."""
    import logging
    logging.getLogger('simplest_agent').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


@pytest.fixture
def performance_test_data():
    """Provide data for performance testing."""
    return {
        'expressions': ['2 + 2'] * 100,  # Simple repeated expressions
        'expected_time_limit': 1.0,      # Maximum seconds for batch processing
        'concurrent_requests': 10         # Number of concurrent operations
    }
