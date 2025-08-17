#!/usr/bin/env python3
"""
Comprehensive Test Suite for Health Checker System
Test all health monitoring and status reporting functionality.
"""

import time
import sys
from unittest.mock import Mock, patch
from contextlib import contextmanager

# Import the agent and health checker
from simplest_agent import (
    HealthChecker, HealthStatus, SystemHealthReport, 
    AgentConfig, ErrorHandler, CircuitBreaker,
    CalculatorTool, initialize_llm
)

def test_health_status_creation():
    """Test HealthStatus data structure creation."""
    print("\n🔍 Testing HealthStatus Creation...")
    
    # Test healthy status
    status = HealthStatus(
        component="test_component",
        status="healthy",
        details={"test": "data"},
        response_time_ms=100.5
    )
    
    assert status.component == "test_component"
    assert status.status == "healthy"
    assert status.details == {"test": "data"}
    assert status.response_time_ms == 100.5
    assert status.error_message is None
    
    # Test unhealthy status with error
    error_status = HealthStatus(
        component="error_component",
        status="unhealthy",
        details={"error_type": "connection_failed"},
        error_message="Connection refused"
    )
    
    assert error_status.status == "unhealthy"
    assert error_status.error_message == "Connection refused"
    print("✅ HealthStatus creation tests passed")


def test_health_checker_initialization():
    """Test HealthChecker initialization with components."""
    print("\n🔍 Testing HealthChecker Initialization...")
    
    # Create mock components
    mock_llm = Mock()
    mock_tools = [Mock(name="test_tool", description="Test tool")]
    mock_circuit_breaker = Mock()
    mock_error_handler = Mock()
    mock_config = Mock()
    
    # Initialize health checker
    health_checker = HealthChecker(
        llm=mock_llm,
        tools=mock_tools,
        circuit_breaker=mock_circuit_breaker,
        error_handler=mock_error_handler,
        config=mock_config
    )
    
    assert health_checker.llm == mock_llm
    assert health_checker.tools == mock_tools
    assert health_checker.circuit_breaker == mock_circuit_breaker
    assert health_checker.error_handler == mock_error_handler
    assert health_checker.config == mock_config
    assert health_checker.health_check_interval == 30
    
    print("✅ HealthChecker initialization tests passed")


def test_tool_availability_checking():
    """Test tool availability validation."""
    print("\n🔍 Testing Tool Availability Checking...")
    
    # Create real calculator tool
    calculator_tool = CalculatorTool()
    error_handler = ErrorHandler()
    
    health_checker = HealthChecker(
        llm=None,
        tools=[calculator_tool],
        error_handler=error_handler
    )
    
    # Test tool availability
    tool_statuses = health_checker.check_tool_availability()
    
    assert len(tool_statuses) == 1
    calc_status = tool_statuses[0]
    assert calc_status.component == "tool_calculator"
    assert calc_status.status == "healthy"
    assert "test_calculation" in calc_status.details
    assert calc_status.details["result"] in ["4", "4.0"]
    assert calc_status.response_time_ms is not None
    
    print(f"✅ Tool availability check passed: {calc_status.details['result']}")


def test_circuit_breaker_status_checking():
    """Test circuit breaker status monitoring."""
    print("\n🔍 Testing Circuit Breaker Status Checking...")
    
    # Create real circuit breaker
    circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
    
    health_checker = HealthChecker(
        circuit_breaker=circuit_breaker,
        error_handler=ErrorHandler()
    )
    
    # Test healthy circuit breaker
    cb_status = health_checker.check_circuit_breaker_status()
    
    assert cb_status.component == "circuit_breaker"
    assert cb_status.status == "healthy"
    assert cb_status.details["state"] == "closed"
    assert cb_status.details["failure_count"] == 0
    assert cb_status.details["failure_threshold"] == 5
    assert cb_status.details["timeout"] == 60
    assert cb_status.error_message is None
    
    # Test circuit breaker after failures
    circuit_breaker.record_failure()
    circuit_breaker.record_failure() 
    
    cb_status_after_failures = health_checker.check_circuit_breaker_status()
    assert cb_status_after_failures.details["failure_count"] == 2
    assert cb_status_after_failures.status == "healthy"  # Still below threshold
    
    print("✅ Circuit breaker status checking tests passed")


@contextmanager
def mock_llm_response(response_content="OK", should_fail=False):
    """Context manager to mock LLM responses."""
    if should_fail:
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("Connection failed")
        yield mock_llm
    else:
        mock_response = Mock()
        mock_response.content = response_content
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        yield mock_llm


def test_model_connectivity_checking():
    """Test LLM model connectivity validation."""
    print("\n🔍 Testing Model Connectivity Checking...")
    
    error_handler = ErrorHandler()
    config = AgentConfig()
    
    # Test healthy LLM
    with mock_llm_response("OK") as mock_llm:
        health_checker = HealthChecker(
            llm=mock_llm,
            error_handler=error_handler,
            config=config
        )
        
        llm_status = health_checker.check_model_connectivity()
        
        assert llm_status.component == "llm_model"
        assert llm_status.status == "healthy"
        assert llm_status.details["test_successful"] is True
        assert llm_status.response_time_ms is not None
        assert llm_status.response_time_ms > 0
        
    print("✅ Healthy model connectivity test passed")
    
    # Test failed LLM connection
    with mock_llm_response(should_fail=True) as mock_llm:
        health_checker = HealthChecker(
            llm=mock_llm,
            error_handler=error_handler,
            config=config
        )
        
        llm_status = health_checker.check_model_connectivity()
        
        assert llm_status.component == "llm_model"
        assert llm_status.status == "unhealthy"
        assert llm_status.error_message is not None
        assert "Connection failed" in llm_status.error_message
        
    print("✅ Failed model connectivity test passed")
    
    # Test no LLM initialized
    health_checker = HealthChecker(
        llm=None,
        error_handler=error_handler,
        config=config
    )
    
    llm_status = health_checker.check_model_connectivity()
    assert llm_status.status == "unhealthy"
    assert "not initialized" in llm_status.details["error"]
    
    print("✅ No LLM initialization test passed")


def test_performance_metrics_collection():
    """Test performance metrics gathering."""
    print("\n🔍 Testing Performance Metrics Collection...")
    
    circuit_breaker = CircuitBreaker()
    error_handler = ErrorHandler()
    config = AgentConfig()
    
    health_checker = HealthChecker(
        circuit_breaker=circuit_breaker,
        error_handler=error_handler,
        config=config
    )
    
    metrics = health_checker.get_performance_metrics()
    
    # Validate metrics structure
    assert "timestamp" in metrics
    assert "circuit_breaker" in metrics
    assert "error_statistics" in metrics
    assert "configuration" in metrics
    
    # Validate circuit breaker metrics
    cb_metrics = metrics["circuit_breaker"]
    assert "state" in cb_metrics
    assert "failure_count" in cb_metrics
    
    # Validate configuration metrics
    config_metrics = metrics["configuration"]
    assert "model" in config_metrics
    assert "provider" in config_metrics
    assert "max_iterations" in config_metrics
    assert "retry_max_attempts" in config_metrics
    
    print("✅ Performance metrics collection tests passed")


def test_comprehensive_health_check():
    """Test complete system health check functionality."""
    print("\n🔍 Testing Comprehensive Health Check...")
    
    # Use real components for integration test
    calculator_tool = CalculatorTool()
    circuit_breaker = CircuitBreaker()
    error_handler = ErrorHandler()
    config = AgentConfig()
    
    with mock_llm_response("System OK") as mock_llm:
        health_checker = HealthChecker(
            llm=mock_llm,
            tools=[calculator_tool],
            circuit_breaker=circuit_breaker,
            error_handler=error_handler,
            config=config
        )
        
        # Perform comprehensive health check
        start_time = time.time()
        health_report = health_checker.perform_comprehensive_health_check()
        check_duration = time.time() - start_time
        
        # Validate report structure
        assert isinstance(health_report, SystemHealthReport)
        assert health_report.overall_status in ["healthy", "degraded", "unhealthy"]
        assert len(health_report.components) >= 3  # LLM, tool, circuit breaker
        assert health_report.performance_metrics is not None
        assert health_report.error_statistics is not None
        assert health_report.timestamp is not None
        
        # Validate components
        component_names = {comp.component for comp in health_report.components}
        expected_components = {"llm_model", "tool_calculator", "circuit_breaker"}
        assert expected_components.issubset(component_names)
        
        # Validate performance metrics include health check duration
        assert "health_check_duration_ms" in health_report.performance_metrics
        assert health_report.performance_metrics["health_check_duration_ms"] > 0
        
        # Check that health check duration is reasonable
        assert check_duration < 5.0  # Should complete in under 5 seconds
        
        print(f"✅ Comprehensive health check passed in {check_duration:.2f}s")
        print(f"   Overall status: {health_report.overall_status}")
        print(f"   Components checked: {len(health_report.components)}")


def test_status_summary_generation():
    """Test status summary for monitoring endpoints."""
    print("\n🔍 Testing Status Summary Generation...")
    
    calculator_tool = CalculatorTool()
    circuit_breaker = CircuitBreaker()
    error_handler = ErrorHandler()
    config = AgentConfig()
    
    with mock_llm_response("Ready") as mock_llm:
        health_checker = HealthChecker(
            llm=mock_llm,
            tools=[calculator_tool],
            circuit_breaker=circuit_breaker,
            error_handler=error_handler,
            config=config
        )
        
        status_summary = health_checker.get_status_summary()
        
        # Validate summary structure
        assert "status" in status_summary
        assert "timestamp" in status_summary
        assert "components" in status_summary
        assert "metrics" in status_summary
        assert "error_stats" in status_summary
        
        # Validate status
        assert status_summary["status"] in ["healthy", "degraded", "unhealthy"]
        
        # Validate metrics
        metrics = status_summary["metrics"]
        assert "total_components" in metrics
        assert "healthy_components" in metrics
        assert "degraded_components" in metrics
        assert "unhealthy_components" in metrics
        
        # Validate component counts add up
        total = metrics["total_components"]
        healthy = metrics["healthy_components"]
        degraded = metrics["degraded_components"]
        unhealthy = metrics["unhealthy_components"]
        assert healthy + degraded + unhealthy == total
        
        print(f"✅ Status summary generation passed")
        print(f"   Status: {status_summary['status']}")
        print(f"   Components: {healthy}/{total} healthy")


def test_error_handling_during_health_checks():
    """Test error handling during health check operations."""
    print("\n🔍 Testing Error Handling During Health Checks...")
    
    error_handler = ErrorHandler()
    
    # Test with failing tool
    from langchain.tools import BaseTool
    from pydantic import BaseModel
    
    class FailingCalculatorTool(BaseTool):
        name: str = "calculator"  # Use calculator name so it gets tested
        description: str = "A calculator that always fails"
        
        def _run(self, input_str: str) -> str:
            raise Exception("Tool failure")
    
    failing_tool = FailingCalculatorTool()
    
    health_checker = HealthChecker(
        tools=[failing_tool],
        error_handler=error_handler
    )
    
    tool_statuses = health_checker.check_tool_availability()
    assert len(tool_statuses) == 1
    
    failing_status = tool_statuses[0]
    
    assert failing_status.component == "tool_calculator"
    assert failing_status.status == "unhealthy"
    assert failing_status.error_message is not None
    assert "Tool failure" in failing_status.error_message
    
    print("✅ Error handling during health checks passed")


def run_all_tests():
    """Run the complete health checker test suite."""
    print("🧪 Health Checker Test Suite")
    print("=" * 50)
    
    test_functions = [
        test_health_status_creation,
        test_health_checker_initialization,
        test_tool_availability_checking,
        test_circuit_breaker_status_checking,
        test_model_connectivity_checking,
        test_performance_metrics_collection,
        test_comprehensive_health_check,
        test_status_summary_generation,
        test_error_handling_during_health_checks
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} FAILED: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"🧪 Test Results: {passed} passed, {failed} failed")
    
    if failed > 0:
        print(f"❌ {failed} test(s) failed")
        return False
    else:
        print("✅ All health checker tests passed!")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
