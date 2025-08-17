# Testing Documentation

This document describes how to run tests in the agentics project using pytest.

## Quick Start

Run all tests:
```bash
pytest tests/
```

Run tests with coverage:
```bash
pytest tests/ --cov=simplest_agent --cov-report=html
```

Use the test runner script:
```bash
./scripts/test_runner.sh all
```

## Test Organization

The test suite is organized into the following structure:

```
tests/
├── __init__.py
├── conftest.py              # pytest fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_calculator.py   # SafeCalculator and CalculatorTool tests
│   ├── test_config.py       # AgentConfig tests
│   ├── test_error_handling.py    # Error handling tests
│   └── test_retry_mechanisms.py  # Retry and circuit breaker tests
├── integration/             # Integration tests
│   └── test_health_monitoring.py # Health monitoring system tests
└── fixtures/                # Test data and utilities
    ├── __init__.py
    └── sample_data.py       # Shared test data
```

## Test Categories

Tests are marked with pytest markers to enable selective execution:

- `unit` - Unit tests for individual components
- `integration` - Integration tests for system-level functionality
- `security` - Security validation tests
- `slow` - Slow-running tests that may be skipped for fast feedback

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_calculator.py -v

# Run specific test class
pytest tests/unit/test_calculator.py::TestSafeCalculator -v

# Run specific test method
pytest tests/unit/test_calculator.py::TestSafeCalculator::test_basic_arithmetic_operations -v
```

### Running by Category

```bash
# Run only unit tests
pytest -m unit -v

# Run only integration tests
pytest -m integration -v

# Run only security tests
pytest -m security -v

# Run only slow tests
pytest -m slow -v

# Run fast tests (exclude slow)
pytest -m "not slow" -v
```

### Coverage Reports

```bash
# Terminal coverage report
pytest tests/ --cov=simplest_agent --cov-report=term-missing

# HTML coverage report
pytest tests/ --cov=simplest_agent --cov-report=html:htmlcov

# Both terminal and HTML
pytest tests/ --cov=simplest_agent --cov-report=term-missing --cov-report=html:htmlcov
```

### Using the Test Runner Script

The `scripts/test_runner.sh` script provides convenient shortcuts:

```bash
# Show help
./scripts/test_runner.sh help

# Run all tests
./scripts/test_runner.sh all

# Run unit tests only
./scripts/test_runner.sh unit

# Run with coverage
./scripts/test_runner.sh coverage-html

# Run security tests
./scripts/test_runner.sh security

# Run specific component tests
./scripts/test_runner.sh calculator
./scripts/test_runner.sh config
./scripts/test_runner.sh error
./scripts/test_runner.sh retry
./scripts/test_runner.sh health
```

## Configuration

Test configuration is defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "--tb=short",
    "--cov=agentics",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov"
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "security: Security validation tests",
    "slow: Slow-running tests"
]
```

## Fixtures

Common test fixtures are defined in `tests/conftest.py`:

- `agent_config()` - Provides test AgentConfig instance
- `mock_llm()` - Mock LLM for testing
- `calculator()` - SafeCalculator instance
- `error_handler()` - ErrorHandler instance
- `circuit_breaker()` - CircuitBreaker instance
- And many more...

## Test Data

Shared test data and utilities are available in `tests/fixtures/sample_data.py`.

## Continuous Integration

For CI/CD integration, use:

```bash
# Run tests with JUnit XML output
pytest tests/ --junitxml=test-results.xml

# Run with coverage for CI
pytest tests/ --cov=simplest_agent --cov-report=xml --cov-report=term
```

## Debugging Tests

```bash
# Run with detailed output on failures
pytest tests/ --tb=long -v

# Run with Python debugger on failures
pytest tests/ --pdb

# Run specific test with maximum verbosity
pytest tests/unit/test_calculator.py::TestSafeCalculator::test_basic_arithmetic_operations -vv

# Stop on first failure
pytest tests/ -x
```

## Test Development Guidelines

### Writing Tests

1. Use descriptive test names that explain what is being tested
2. Follow the Arrange-Act-Assert pattern
3. Use appropriate pytest markers for categorization
4. Leverage existing fixtures from `conftest.py`
5. Add parametrized tests for testing multiple scenarios

### Example Test Structure

```python
class TestFeatureName:
    """Test suite for FeatureName functionality."""

    def test_basic_functionality(self, fixture_name):
        """Test basic feature functionality."""
        # Arrange
        setup_data = create_test_data()

        # Act
        result = feature_under_test.method(setup_data)

        # Assert
        assert result == expected_value
        assert some_side_effect_occurred()

    @pytest.mark.parametrize("input,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
    ])
    def test_parametrized_behavior(self, input, expected):
        """Test feature with different inputs."""
        result = feature_under_test.method(input)
        assert result == expected

    @pytest.mark.security
    def test_security_validation(self):
        """Test security-related functionality."""
        with pytest.raises(SecurityError):
            feature_under_test.dangerous_method()
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure the project root is in Python path
2. **Fixture not found**: Check that fixtures are defined in `conftest.py` or imported properly
3. **Slow tests**: Use `-m "not slow"` to skip slow tests during development
4. **Coverage issues**: Make sure the module being tested is properly imported

### Environment Setup

Tests require the development dependencies to be installed:

```bash
# Using uv (recommended)
uv sync --dev

# Using pip
pip install -e ".[dev]"
```

## Performance

Current test suite statistics:
- **Total tests**: 140+
- **Unit tests**: ~110
- **Integration tests**: ~30
- **Security tests**: ~15
- **Slow tests**: ~5
- **Average run time**: ~10 seconds (excluding slow tests)
- **Coverage**: 90%+ (target)

The test suite is designed to provide fast feedback during development while ensuring comprehensive coverage of all functionality.
