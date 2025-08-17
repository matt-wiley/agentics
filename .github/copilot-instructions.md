# AI Coding Agent Instructions for Agentics

## Prerequisites

Review the following files to understand how you should act and what you should know before working with this project:
- `.github/instructions/memory.instructions.md`: Contains all memorized information


## Project Overview
This is a study project focused on LLM Agentic Applications, featuring a security-focused single-file agent implementation (`simplest_agent.py`) that uses LangChain + Ollama with a custom SafeCalculator tool.

## Core Architecture

### Single-File Agent Pattern
- **Main Implementation**: `simplest_agent.py` - Complete LangChain agent in ~1,450 lines with enterprise features
- **Key Constraint**: Maintain single-file architecture while adding enterprise features
- **Structure Sections**: Configuration → Security → Tools → Agent → Main (see MODERNIZATION_WORKPLAN.md)
- **Enterprise Features**: Error handling, circuit breakers, retry mechanisms, health monitoring, comprehensive configuration

### Security-First Design
The project prioritizes security over convenience:
```python
# NEVER use eval() - use SafeCalculator instead
calculator = SafeCalculator()  # AST-based parsing
result = calculator.evaluate_expression(expression)  # Safe evaluation
```

### Tool Integration Pattern
Custom tools inherit from `BaseTool` with Pydantic validation:
```python
class CalculatorTool(BaseTool):
    name: str = "calculator" 
    description: str = "Useful for when you need to answer questions about math"
    
    def _run(self, expression: str) -> str:
        # Implement with SafeCalculator, never eval()
```

## Development Workflow

### Task-Driven Development
Follow the structured modernization workplan in `notes/MODERNIZATION_WORKPLAN.md`:
- **Phase 1**: pytest Migration & Testing Infrastructure ✅ **COMPLETED**
- **Phase 2**: Code Architecture Modularization
- **Phase 3**: Enhanced Documentation & Maintainability
- **Phase 4**: Performance & Security Hardening

### Testing Strategy
**Professional pytest Infrastructure** (Phase 1 completed):
- **143 comprehensive tests** organized in `tests/` directory
- **Unit tests**: `tests/unit/` - 113 tests with 100% pass rate
- **Integration tests**: `tests/integration/` - 30 tests for system-level validation
- **Security tests**: Marked with `@pytest.mark.security` decorator
- **Test execution**: Use `./scripts/test_runner.sh` for convenient test running
- **Coverage reporting**: pytest-cov integration with HTML reports
- Run `demo_safe_calculator.py` for functionality demo
- Validate against malicious inputs (injection patterns blocked)
- Validate against malicious inputs (injection patterns blocked)

### Environment Setup
```bash
# Python virtual environment with uv
uv sync  # Install dependencies from pyproject.toml
source .venv/bin/activate
python simplest_agent.py  # Requires Ollama running locally
```

## Critical Patterns

### Security Validation
Always implement multi-layer security for user inputs:
1. **Pattern Detection**: Block `__`, `import`, `exec`, `eval`, etc.
2. **Character Filtering**: Allow only mathematical chars for calculator
3. **Length Limits**: Prevent DoS with input size restrictions
4. **AST Parsing**: Use `ast` module instead of string execution

### Enterprise-Grade Error Handling
The project implements comprehensive error handling:
```python
try:
    result = some_operation()
    return str(result)
except Exception as e:
    return f"Error: {str(e)}"
```
- **AgentError**: Custom exception with error categorization
- **ErrorHandler**: Central error processing with logging
- **Circuit Breaker**: Fail-fast patterns for resilience
- **Retry Logic**: Exponential backoff with jitter

### Memory Management 
The agent uses `ConversationBufferMemory` - consider summarization for long sessions as per modernization workplan.

### Model Configuration
- **Default Model**: `llama3.2:3b` via Ollama
- **Extensible**: Support multiple providers (OpenAI, etc.) via environment variables
- **Local-First**: Assumes local Ollama deployment at `http://127.0.0.1:11434`

## Code Quality Standards

### Single-File Organization
Use clear section separators following the template in `MODERNIZATION_WORKPLAN.md`:
```python
# ==========================================================
#   Section Name
# ==========================================================
```

### Error Handling
All operations must have comprehensive error handling:
```python
try:
    result = some_operation()
    return str(result)
except Exception as e:
    return f"Error: {str(e)}"
```

### Documentation
- Comprehensive docstrings for all classes and methods
- Security rationale for SafeCalculator implementation
- Task completion summaries (see `TASK_1_1_SUMMARY.md`)

## Integration Knowledge

### LangChain Patterns
- Uses deprecated `initialize_agent` (Task 4.1 plans ReAct replacement)  
- `AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION` for conversational flow
- Custom tools require Pydantic models for input validation

### Dependencies
Minimal dependency strategy from `pyproject.toml`:
- `langchain>=0.3.27` (core framework)
- `langchain-ollama>=0.3.6` (local model integration)
- `langchain-community>=0.3.27` (additional tools)
- **Development Dependencies**: `pytest>=8.0.0`, `pytest-cov`, `pytest-mock`, `pytest-asyncio`

## File Structure Understanding
- `main.py`: Basic hello world (not the main agent)
- `simplest_agent.py`: The actual LLM agent implementation
- `notes/`: Comprehensive guides on LLM agents and protocols
- `tests/`: Professional pytest infrastructure with unit and integration tests
- `scripts/`: Test execution and development utilities
- `MODERNIZATION_WORKPLAN.md`: Structured improvement roadmap with phases

## Development Priorities
1. **Security First**: Never compromise on input validation and safe evaluation
2. **Single-File Constraint**: Maintain simplicity while adding enterprise features
3. **Task-Based Progress**: Follow workplan phases systematically
4. **Comprehensive Testing**: Validate both functionality and security
5. **Documentation**: Document security rationale and implementation decisions

## Current Development Status
- **Phase 1 Complete**: Professional pytest infrastructure with 143 tests (96% pass rate)
- **Legacy Files Removed**: All custom test files have been migrated to pytest
- **Ready for Phase 2**: Code architecture modularization can begin
- **Enterprise Features**: Circuit breakers, retry mechanisms, health monitoring implemented

When modifying this codebase, always consider the security implications first, maintain the single-file architecture constraint, and follow the structured workplan for systematic improvements.
