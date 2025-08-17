"""
Test suite for retry mechanisms and circuit breaker functionality.

This module contains pytest tests for the retry decorator and circuit breaker
components, ensuring proper failure handling and resilience patterns.
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Callable

# Import components from main agent module
from simplest_agent import CircuitBreaker, retry_with_backoff, CalculatorTool


class TestCircuitBreaker:
    """Test suite for CircuitBreaker functionality."""

    def test_initial_state(self):
        """Test circuit breaker starts in closed state."""
        cb = CircuitBreaker(failure_threshold=3, timeout=5)

        assert cb.state == 'closed'
        assert cb.is_available() is True

    def test_failure_threshold_behavior(self):
        """Test circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3, timeout=5)

        # Record failures up to threshold - 1
        for i in range(2):
            cb.record_failure()
            assert cb.state == 'closed'
            assert cb.is_available() is True

        # One more failure should open the circuit
        cb.record_failure()
        assert cb.state == 'open'
        assert cb.is_available() is False

    def test_success_resets_circuit(self):
        """Test that success resets the circuit breaker."""
        cb = CircuitBreaker(failure_threshold=2, timeout=5)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == 'open'

        # Success should reset it
        cb.record_success()
        assert cb.state == 'closed'
        assert cb.is_available() is True

    def test_half_open_state_transitions(self):
        """Test half-open state behavior after timeout."""
        cb = CircuitBreaker(failure_threshold=2, timeout=0.1)  # Very short timeout

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == 'open'

        # Wait for timeout
        time.sleep(0.2)

        # Check availability should transition to half-open
        assert cb.is_available() is True
        assert cb.state == 'half-open'

        # Success should close it
        cb.record_success()
        assert cb.state == 'closed'

    def test_half_open_failure_reopens(self):
        """Test that failure in half-open state reopens circuit."""
        cb = CircuitBreaker(failure_threshold=2, timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == 'open'

        # Wait for timeout to half-open
        time.sleep(0.2)

        # Check availability should transition to half-open
        assert cb.is_available() is True
        assert cb.state == 'half-open'

        # Failure should reopen
        cb.record_failure()
        assert cb.state == 'open'

    @pytest.mark.parametrize("threshold,timeout", [
        (1, 1),
        (3, 5),
        (5, 10),
    ])
    def test_different_configurations(self, threshold: int, timeout: int):
        """Test circuit breaker with different threshold and timeout values."""
        cb = CircuitBreaker(failure_threshold=threshold, timeout=timeout)

        # Should remain closed until threshold
        for i in range(threshold - 1):
            cb.record_failure()
            assert cb.state == 'closed'

        # Final failure should open
        cb.record_failure()
        assert cb.state == 'open'


class TestRetryDecorator:
    """Test suite for retry_with_backoff decorator."""

    def test_successful_function_no_retry(self):
        """Test that successful function executes without retries."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def success_function():
            nonlocal call_count
            call_count += 1
            return "Success!"

        result = success_function()

        assert result == "Success!"
        assert call_count == 1

    def test_eventual_success_with_retries(self):
        """Test function that succeeds after some failures."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return "Success!"

        start_time = time.time()
        result = flaky_function()
        elapsed = time.time() - start_time

        assert result == "Success!"
        assert call_count == 3
        assert elapsed >= 0.3  # Should have waited for retries

    def test_retry_exhaustion(self):
        """Test behavior when all retries are exhausted."""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.1)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception(f"Attempt {call_count} failed")

        with pytest.raises(Exception, match="Attempt 3 failed"):
            always_fail()

        assert call_count == 3  # Initial + 2 retries

    def test_exponential_backoff_timing(self):
        """Test that retry delays follow exponential backoff pattern."""
        call_times = []

        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def timing_test():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise Exception("Retry me")
            return "Done"

        timing_test()

        assert len(call_times) == 3
        # Check approximate delays (0.1s, 0.2s)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        assert 0.08 <= delay1 <= 0.15  # ~0.1s with some tolerance
        assert 0.15 <= delay2 <= 0.25  # ~0.2s with some tolerance

    @pytest.mark.parametrize("max_retries,base_delay", [
        (1, 0.1),
        (2, 0.05),
        (4, 0.2),
    ])
    def test_different_retry_configurations(self, max_retries: int, base_delay: float):
        """Test retry decorator with different configurations."""
        call_count = 0

        @retry_with_backoff(max_retries=max_retries, base_delay=base_delay)
        def configurable_function():
            nonlocal call_count
            call_count += 1
            if call_count <= max_retries:
                raise Exception(f"Attempt {call_count}")
            return "Success"

        result = configurable_function()
        assert result == "Success"
        assert call_count == max_retries + 1


class TestCircuitBreakerIntegration:
    """Test suite for circuit breaker integration with retry mechanisms."""

    def test_circuit_breaker_with_retry(self):
        """Test circuit breaker integration with retry decorator."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.1, circuit_breaker=cb)
        def failing_service():
            nonlocal call_count
            call_count += 1
            raise Exception(f"Service failure {call_count}")

        # First attempt should exhaust retries and open circuit
        with pytest.raises(Exception):
            failing_service()

        assert cb.state == 'open'

        # Next attempt should fail immediately due to open circuit
        call_count = 0
        with pytest.raises(Exception, match="temporarily unavailable"):
            failing_service()

        assert call_count == 0  # Should not have called the function

    def test_circuit_breaker_allows_success_after_timeout(self):
        """Test circuit breaker allows calls after timeout period."""
        cb = CircuitBreaker(failure_threshold=1, timeout=0.1)
        call_count = 0

        @retry_with_backoff(max_retries=1, base_delay=0.05, circuit_breaker=cb)
        def sometimes_works():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first two times
                raise Exception("Service down")
            return "Service up!"

        # First call fails and opens circuit
        with pytest.raises(Exception):
            sometimes_works()

        assert cb.state == 'open'

        # Wait for circuit to go half-open
        time.sleep(0.2)

        # This should succeed and close the circuit
        result = sometimes_works()
        assert result == "Service up!"
        assert cb.state == 'closed'

    def test_circuit_breaker_without_retry(self):
        """Test circuit breaker functionality without retry decorator."""
        cb = CircuitBreaker(failure_threshold=2, timeout=0.1)

        # Manual failure recording
        cb.record_failure()
        assert cb.is_available()

        cb.record_failure()
        assert not cb.is_available()

        # Wait for timeout
        time.sleep(0.2)

        # Check availability should transition to half-open
        assert cb.is_available() is True
        assert cb.state == 'half-open'

        # Success should close it
        cb.record_success()
        assert cb.is_available()
        assert cb.state == 'closed'


class TestCalculatorToolRetry:
    """Test suite for calculator tool with retry functionality."""

    def test_calculator_tool_normal_operation(self):
        """Test calculator tool works normally with retry wrapper."""
        calc_tool = CalculatorTool()

        result = calc_tool._run("2 + 3 * 4")
        assert "14" in result

    def test_calculator_tool_error_handling(self):
        """Test calculator tool handles errors gracefully."""
        calc_tool = CalculatorTool()

        result = calc_tool._run("invalid expression")
        assert "Error:" in result

    @pytest.mark.parametrize("expression,expected", [
        ("1 + 1", "2"),
        ("10 / 2", "5"),
        ("3 * 3", "9"),
        ("(5 + 3) * 2", "16"),
    ])
    def test_calculator_expressions(self, expression: str, expected: str):
        """Test calculator tool with various valid expressions."""
        calc_tool = CalculatorTool()

        result = calc_tool._run(expression)
        assert expected in result

    @pytest.mark.security
    @pytest.mark.parametrize("malicious_input", [
        "__import__('os').system('ls')",
        "exec('print(\"hacked\")')",
        "eval('1+1')",
        "import os; os.system('pwd')",
    ])
    def test_calculator_security_with_retry(self, malicious_input: str):
        """Test calculator tool blocks malicious input even with retry."""
        calc_tool = CalculatorTool()

        result = calc_tool._run(malicious_input)
        assert "Error:" in result
        assert "security" in result.lower()


class TestRetryDecoratorEdgeCases:
    """Test suite for retry decorator edge cases and error conditions."""

    def test_zero_retries(self):
        """Test retry decorator with zero retries."""
        call_count = 0

        @retry_with_backoff(max_retries=0, base_delay=0.1)
        def no_retry_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Failed")

        with pytest.raises(Exception, match="Failed"):
            no_retry_function()

        assert call_count == 1  # Should only call once

    def test_very_small_delay(self):
        """Test retry decorator with very small delays."""
        @retry_with_backoff(max_retries=2, base_delay=0.001)
        def fast_retry():
            raise Exception("Quick fail")

        start_time = time.time()
        with pytest.raises(Exception):
            fast_retry()
        elapsed = time.time() - start_time

        # Should complete very quickly
        assert elapsed < 0.1

    def test_exception_preservation(self):
        """Test that original exception details are preserved."""
        @retry_with_backoff(max_retries=1, base_delay=0.1)
        def specific_error():
            raise ValueError("Specific error message")

        # The retry decorator wraps exceptions in AgentError
        with pytest.raises(Exception) as exc_info:
            specific_error()

        # Check that the original error message is preserved somewhere
        error_str = str(exc_info.value)
        assert "Specific error message" in error_str

    def test_return_value_preservation(self):
        """Test that return values are properly preserved."""
        @retry_with_backoff(max_retries=2, base_delay=0.1)
        def return_complex_object():
            return {"key": "value", "list": [1, 2, 3], "nested": {"inner": True}}

        result = return_complex_object()
        expected = {"key": "value", "list": [1, 2, 3], "nested": {"inner": True}}
        assert result == expected


@pytest.mark.slow
class TestRetryTimingBehavior:
    """Test suite for retry timing behavior (marked as slow)."""

    def test_total_retry_duration(self):
        """Test total duration of retry attempts."""
        @retry_with_backoff(max_retries=3, base_delay=0.1)
        def duration_test():
            raise Exception("Always fail")

        start_time = time.time()
        with pytest.raises(Exception):
            duration_test()
        total_duration = time.time() - start_time

        # Should be roughly: 0.1 + 0.2 + 0.4 = 0.7 seconds
        assert 0.6 <= total_duration <= 1.0

    def test_jitter_in_delays(self):
        """Test that jitter is applied to delays (if implemented)."""
        delays = []

        @retry_with_backoff(max_retries=5, base_delay=0.1)
        def jitter_test():
            if len(delays) > 0:
                delays.append(time.time())
            else:
                delays.append(time.time())
            raise Exception("Test jitter")

        with pytest.raises(Exception):
            jitter_test()

        # Check that we have multiple delay measurements
        assert len(delays) == 6  # Initial + 5 retries

        # Calculate actual delays
        actual_delays = [delays[i+1] - delays[i] for i in range(len(delays)-1)]

        # Delays should be roughly 0.1, 0.2, 0.4, 0.8, 1.6
        # But might have jitter, so we check ranges
        assert len(actual_delays) == 5
        assert 0.08 <= actual_delays[0] <= 0.15  # First retry delay
        assert 0.15 <= actual_delays[1] <= 0.25  # Second retry delay
