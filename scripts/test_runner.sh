#!/bin/bash
# Test execution scripts for the agentics project
# This file provides convenient commands for running different types of tests

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}Agentics Test Suite${NC}"
echo "====================="
echo "Project root: $PROJECT_ROOT"
echo ""

# Function to run pytest with proper Python path
run_pytest() {
    cd "$PROJECT_ROOT"
    if [ -f ".venv/bin/python" ]; then
        echo -e "${GREEN}Using virtual environment: .venv/bin/python${NC}"
        .venv/bin/python -m pytest "$@"
    else
        echo -e "${YELLOW}No virtual environment found, using system python${NC}"
        python -m pytest "$@"
    fi
}

# Parse command line arguments
case "${1:-all}" in
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  all             - Run all tests (default)"
        echo "  unit            - Run only unit tests"
        echo "  integration     - Run only integration tests"
        echo "  security        - Run only security-related tests"
        echo "  slow            - Run only slow-running tests"
        echo "  fast            - Run tests excluding slow ones"
        echo "  coverage        - Run tests with coverage reporting"
        echo "  coverage-html   - Run tests with HTML coverage report"
        echo "  verbose         - Run all tests with verbose output"
        echo "  calculator      - Run only calculator-related tests"
        echo "  config          - Run only configuration tests"
        echo "  error           - Run only error handling tests"
        echo "  retry           - Run only retry mechanism tests"
        echo "  health          - Run only health monitoring tests"
        echo "  watch           - Run tests in watch mode (requires pytest-watch)"
        echo "  help            - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 unit"
        echo "  $0 coverage-html"
        echo "  $0 security"
        ;;

    "all")
        echo -e "${GREEN}Running all tests...${NC}"
        run_pytest tests/ -v
        ;;

    "unit")
        echo -e "${GREEN}Running unit tests...${NC}"
        run_pytest tests/unit/ -v
        ;;

    "integration")
        echo -e "${GREEN}Running integration tests...${NC}"
        run_pytest tests/integration/ -v
        ;;

    "security")
        echo -e "${GREEN}Running security tests...${NC}"
        run_pytest -m security -v
        ;;

    "slow")
        echo -e "${YELLOW}Running slow tests...${NC}"
        run_pytest -m slow -v
        ;;

    "fast")
        echo -e "${GREEN}Running fast tests (excluding slow)...${NC}"
        run_pytest -m "not slow" -v
        ;;

    "coverage")
        echo -e "${GREEN}Running tests with coverage...${NC}"
        run_pytest tests/ --cov=simplest_agent --cov-report=term-missing
        ;;

    "coverage-html")
        echo -e "${GREEN}Running tests with HTML coverage report...${NC}"
        run_pytest tests/ --cov=simplest_agent --cov-report=html:htmlcov --cov-report=term-missing
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        fi
        ;;

    "verbose")
        echo -e "${GREEN}Running all tests with verbose output...${NC}"
        run_pytest tests/ -vv --tb=long
        ;;

    "calculator")
        echo -e "${GREEN}Running calculator tests...${NC}"
        run_pytest tests/unit/test_calculator.py -v
        ;;

    "config")
        echo -e "${GREEN}Running configuration tests...${NC}"
        run_pytest tests/unit/test_config.py -v
        ;;

    "error")
        echo -e "${GREEN}Running error handling tests...${NC}"
        run_pytest tests/unit/test_error_handling.py -v
        ;;

    "retry")
        echo -e "${GREEN}Running retry mechanism tests...${NC}"
        run_pytest tests/unit/test_retry_mechanisms.py -v
        ;;

    "health")
        echo -e "${GREEN}Running health monitoring tests...${NC}"
        run_pytest tests/integration/test_health_monitoring.py -v
        ;;

    "watch")
        echo -e "${YELLOW}Starting test watch mode...${NC}"
        echo "Note: This requires pytest-watch to be installed: pip install pytest-watch"
        cd "$PROJECT_ROOT"
        ptw tests/
        ;;

    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Use '$0 help' to see available commands"
        exit 1
        ;;
esac
