#!/usr/bin/env python3
"""
Test suite for retry mechanisms and circuit breaker functionality.
"""

import sys
import time
import logging
from unittest.mock import patch, MagicMock

# Add the current directory to Python path
sys.path.append('.')

# Import our enhanced agent components
from simplest_agent import CircuitBreaker, retry_with_backoff, RobustAgent

# Configure logging to see retry attempts
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_circuit_breaker():
    """Test circuit breaker functionality."""
    print("🔧 Testing Circuit Breaker...")
    
    cb = CircuitBreaker(failure_threshold=3, timeout=5)
    
    # Initial state should be closed
    assert cb.state == 'closed'
    assert cb.is_available() == True
    print("✅ Circuit breaker starts in closed state")
    
    # Record failures up to threshold
    for i in range(2):
        cb.record_failure()
        assert cb.state == 'closed'
        assert cb.is_available() == True
    
    # One more failure should open the circuit
    cb.record_failure()
    assert cb.state == 'open'
    assert cb.is_available() == False
    print("✅ Circuit breaker opens after threshold failures")
    
    # Test success resets the circuit
    cb.record_success()
    assert cb.state == 'closed'
    assert cb.is_available() == True
    print("✅ Circuit breaker resets after success")


def test_retry_decorator():
    """Test retry decorator with backoff."""
    print("\n🔄 Testing Retry Decorator...")
    
    call_count = 0
    
    @retry_with_backoff(max_retries=3, base_delay=0.1)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception(f"Attempt {call_count} failed")
        return "Success!"
    
    # Should succeed on third attempt
    start_time = time.time()
    result = flaky_function()
    elapsed = time.time() - start_time
    
    assert result == "Success!"
    assert call_count == 3
    assert elapsed >= 0.3  # Should have waited for retries
    print(f"✅ Function succeeded after {call_count} attempts in {elapsed:.2f}s")


def test_retry_exhaustion():
    """Test behavior when all retries are exhausted."""
    print("\n❌ Testing Retry Exhaustion...")
    
    call_count = 0
    
    @retry_with_backoff(max_retries=2, base_delay=0.1)
    def always_fail():
        nonlocal call_count
        call_count += 1
        raise Exception(f"Attempt {call_count} failed")
    
    try:
        always_fail()
        assert False, "Should have raised an exception"
    except Exception as e:
        assert "Attempt 3 failed" in str(e)
        assert call_count == 3  # Initial + 2 retries
        print(f"✅ All retries exhausted after {call_count} attempts")


def test_circuit_breaker_integration():
    """Test circuit breaker integration with retry decorator."""
    print("\n🔌 Testing Circuit Breaker + Retry Integration...")
    
    cb = CircuitBreaker(failure_threshold=2, timeout=1)
    call_count = 0
    
    @retry_with_backoff(max_retries=3, base_delay=0.1, circuit_breaker=cb)
    def failing_service():
        nonlocal call_count
        call_count += 1
        raise Exception(f"Service failure {call_count}")
    
    # First attempt should exhaust retries and open circuit
    try:
        failing_service()
    except Exception:
        pass
    
    assert cb.state == 'open'
    print(f"✅ Circuit opened after {call_count} failures")
    
    # Next attempt should fail immediately due to open circuit
    call_count = 0
    try:
        failing_service()
        assert False, "Should have failed immediately"
    except Exception as e:
        assert "temporarily unavailable" in str(e).lower()
        assert call_count == 0  # Should not have called the function
        print("✅ Circuit breaker blocked subsequent calls")


def test_calculator_tool_retry():
    """Test calculator tool with retry functionality."""
    print("\n🧮 Testing Calculator Tool Retry...")
    
    from simplest_agent import CalculatorTool
    
    calc_tool = CalculatorTool()
    
    # Test normal operation
    result = calc_tool._run("2 + 3 * 4")
    assert "14" in result
    print("✅ Calculator tool works with retry wrapper")
    
    # Test with invalid expression
    result = calc_tool._run("invalid expression")
    assert "Error:" in result
    print("✅ Calculator tool handles errors gracefully")


def main():
    """Run all tests."""
    print("🧪 Starting Retry Mechanism Tests")
    print("=" * 50)
    
    try:
        test_circuit_breaker()
        test_retry_decorator()
        test_retry_exhaustion()
        test_circuit_breaker_integration()
        test_calculator_tool_retry()
        
        print("\n" + "=" * 50)
        print("🎉 All retry mechanism tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
