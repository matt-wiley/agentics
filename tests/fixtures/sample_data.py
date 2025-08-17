"""Sample data and fixtures for tests."""

# Sample mathematical expressions for comprehensive testing
VALID_EXPRESSIONS = [
    ("2 + 2", 4),
    ("10 - 3", 7),
    ("5 * 6", 30),
    ("12 / 4", 3.0),
    ("2 ** 3", 8),
    ("(1 + 2) * 3", 9),
    ("abs(-5)", 5),
    ("max(1, 2, 3)", 3),
    ("min(1, 2, 3)", 1),
    ("round(3.14159, 2)", 3.14),
    ("sqrt(16)", 4.0),
    ("pow(2, 3)", 8),
]

# Security threat patterns that should be blocked
SECURITY_PATTERNS = [
    "__import__",
    "__builtins__",
    "exec",
    "eval",
    "open",
    "file",
    "input", 
    "raw_input",
    "compile",
    "globals",
    "locals",
    "vars",
    "dir",
    "getattr",
    "setattr",
    "delattr",
    "hasattr",
    "callable",
    "isinstance",
    "issubclass",
    "super",
    "staticmethod",
    "classmethod",
    "property",
    "subprocess",
    "os",
    "sys",
    "importlib"
]

# Invalid expressions that should raise validation errors
INVALID_EXPRESSIONS = [
    "2 + abc",
    "undefined_function()",
    "2 +",
    "* 3",
    "((2 + 3)",
    "2 + 3))",
    "2 & 3",  # Bitwise operations not allowed
    "2 | 3",  # Bitwise operations not allowed
    "2 ^ 3",  # Bitwise operations not allowed
    "~2",     # Bitwise operations not allowed
    "2 << 1", # Bitwise operations not allowed
    "2 >> 1", # Bitwise operations not allowed
]

# Environment variable test configurations
ENV_CONFIGS = {
    "minimal_ollama": {
        "AGENT_PROVIDER": "ollama",
        "AGENT_MODEL": "test-model",
        "OLLAMA_BASE_URL": "http://localhost:11434"
    },
    "complete_ollama": {
        "AGENT_PROVIDER": "ollama",
        "AGENT_MODEL": "llama3.2:3b",
        "AGENT_TEMPERATURE": "0.7",
        "AGENT_VERBOSE": "true",
        "AGENT_MAX_ITERATIONS": "10",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "LOG_LEVEL": "INFO"
    },
    "openai_config": {
        "AGENT_PROVIDER": "openai",
        "AGENT_MODEL": "gpt-3.5-turbo",
        "OPENAI_API_KEY": "test-key-12345",
        "OPENAI_API_BASE": "https://api.openai.com/v1"
    },
    "invalid_provider": {
        "AGENT_PROVIDER": "unknown_provider",
        "AGENT_MODEL": "test-model"
    },
    "missing_required": {
        "AGENT_PROVIDER": "openai",
        "AGENT_MODEL": "gpt-3.5-turbo"
        # Missing OPENAI_API_KEY
    }
}

# Health check test scenarios
HEALTH_SCENARIOS = {
    "healthy_system": {
        "components": ["llm", "calculator", "circuit_breaker"],
        "expected_status": "healthy"
    },
    "calculator_error": {
        "components": ["llm", "circuit_breaker"],  # Missing calculator
        "expected_status": "degraded"
    },
    "circuit_breaker_open": {
        "circuit_breaker_failures": 5,  # Trigger threshold
        "expected_status": "unhealthy"
    },
    "llm_connectivity_failure": {
        "llm_error": "Connection timeout",
        "expected_status": "unhealthy"
    }
}

# Error handling test patterns
ERROR_PATTERNS = {
    "security_errors": [
        ("__import__('os')", "security reasons"),
        ("exec('print(1)')", "dangerous pattern"),
        ("eval('2+2')", "security reasons"),
    ],
    "validation_errors": [
        ("2 + abc", "invalid characters"),
        ("undefined_func()", "invalid characters"),
        ("2 +", "invalid expression"),
    ],
    "computation_errors": [
        ("1 / 0", "division by zero"),
        ("2 ** 1000", "result too large"),
    ]
}

# Performance test configurations
PERFORMANCE_CONFIGS = {
    "load_test": {
        "num_requests": 100,
        "expressions": ["2 + 2", "5 * 6", "(1 + 2) * 3"],
        "max_time_seconds": 5.0
    },
    "stress_test": {
        "num_requests": 1000,
        "expressions": ["pow(2, 10)", "max(1, 2, 3, 4, 5)"],
        "max_time_seconds": 30.0
    },
    "concurrent_test": {
        "num_threads": 10,
        "requests_per_thread": 50,
        "expressions": ["sqrt(16)", "abs(-10)"],
        "max_time_seconds": 10.0
    }
}
