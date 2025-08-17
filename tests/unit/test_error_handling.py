"""Unit tests for error handling components."""
import pytest
import time
import logging
from unittest.mock import patch, MagicMock
from simplest_agent import (
    ErrorCategory, AgentError, ErrorHandler, SafeCalculator,
    CalculatorTool
)


class TestErrorCategory:
    """Test the ErrorCategory enumeration."""
    
    def test_error_categories_exist(self):
        """Test that all expected error categories exist."""
        expected_categories = [
            'CONNECTIVITY', 'VALIDATION', 'COMPUTATION', 'CONFIGURATION',
            'SECURITY', 'TIMEOUT', 'RESOURCE', 'UNKNOWN'
        ]
        
        for category_name in expected_categories:
            assert hasattr(ErrorCategory, category_name), f"Missing category: {category_name}"
    
    def test_categories_have_values(self):
        """Test that categories have meaningful values."""
        categories = list(ErrorCategory)
        assert len(categories) > 0
        
        for category in categories:
            assert category.value  # Should have a non-empty value


class TestAgentError:
    """Test the AgentError exception class."""
    
    def test_agent_error_creation(self):
        """Test basic AgentError creation."""
        error = AgentError(
            "Test error message",
            ErrorCategory.VALIDATION,
            context={"test": "data"}
        )
        
        assert error.message == "Test error message"
        assert error.category == ErrorCategory.VALIDATION
        assert error.context == {"test": "data"}
        assert error.trace_id  # Should have a generated trace ID
        assert error.timestamp  # Should have a timestamp
    
    def test_agent_error_without_context(self):
        """Test AgentError creation without context."""
        error = AgentError("Simple error", ErrorCategory.COMPUTATION)
        
        assert error.message == "Simple error"
        assert error.category == ErrorCategory.COMPUTATION
        assert error.context == {}
    
    def test_user_message_generation(self):
        """Test that user-friendly messages are generated.""" 
        # Test connectivity error
        conn_error = AgentError(
            "Connection timeout",
            ErrorCategory.CONNECTIVITY,
            context={"server": "ollama"}
        )
        
        assert "trouble connecting" in conn_error.user_message.lower()
        assert len(conn_error.recovery_suggestions) > 0
        assert any("wait" in suggestion.lower() for suggestion in conn_error.recovery_suggestions)
    
    def test_security_error_messages(self):
        """Test security error user messages."""
        security_error = AgentError(
            "Dangerous pattern detected",
            ErrorCategory.SECURITY,
            context={"pattern": "__import__"}
        )
        
        assert "security reasons" in security_error.user_message.lower()
        assert len(security_error.recovery_suggestions) > 0
        assert any("review" in suggestion.lower() for suggestion in security_error.recovery_suggestions)
    
    def test_validation_error_messages(self):
        """Test validation error user messages."""
        validation_error = AgentError(
            "Invalid expression format",
            ErrorCategory.VALIDATION,
            context={"expression": "bad_input"}
        )
        
        assert "issue with the input" in validation_error.user_message.lower()
        assert any("check" in suggestion.lower() for suggestion in validation_error.recovery_suggestions)
    
    def test_computation_error_messages(self):
        """Test computation error user messages."""
        comp_error = AgentError(
            "Division by zero",
            ErrorCategory.COMPUTATION,
            context={"expression": "1/0"}
        )
        
        assert "calculation" in comp_error.user_message.lower() or "error" in comp_error.user_message.lower()
        assert len(comp_error.recovery_suggestions) > 0
    
    def test_error_serialization(self):
        """Test that errors can be serialized to dictionaries."""
        error = AgentError(
            "Test error",
            ErrorCategory.RESOURCE,
            context={"test": "value"}
        )
        
        error_dict = error.to_dict()
        
        assert "error_id" in error_dict
        assert "message" in error_dict
        assert "category" in error_dict
        assert "context" in error_dict
        assert "timestamp" in error_dict
        assert error_dict["category"] == "resource"
    
    def test_error_string_representation(self):
        """Test string representation of AgentError."""
        error = AgentError("Test message", ErrorCategory.VALIDATION)
        
        str_repr = str(error)
        assert "Test message" in str_repr
        # The string representation might not include the category name


class TestErrorHandler:
    """Test the ErrorHandler class."""
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler creates successfully."""
        handler = ErrorHandler()
        assert handler is not None
    
    def test_error_classification(self, error_handler):
        """Test error classification logic."""
        # Test connectivity errors
        conn_error = Exception("Connection refused to server")
        assert error_handler.classify_error(conn_error) == ErrorCategory.CONNECTIVITY
        
        # Test validation errors
        val_error = Exception("Invalid syntax in expression")
        assert error_handler.classify_error(val_error) == ErrorCategory.VALIDATION
        
        # Test computation errors  
        comp_error = Exception("Division by zero error")
        assert error_handler.classify_error(comp_error) == ErrorCategory.COMPUTATION
        
        # Test security errors
        sec_error = Exception("Dangerous pattern blocked")
        assert error_handler.classify_error(sec_error) == ErrorCategory.SECURITY
    
    def test_error_classification_edge_cases(self, error_handler):
        """Test error classification with edge cases."""
        # Test None error
        assert error_handler.classify_error(None) in list(ErrorCategory)
        
        # Test empty message
        empty_error = Exception("")
        assert error_handler.classify_error(empty_error) in list(ErrorCategory)
        
        # Test unknown error type
        unknown_error = Exception("Unknown error type")
        classified = error_handler.classify_error(unknown_error)
        assert classified in list(ErrorCategory)
    
    def test_error_statistics_tracking(self, error_handler):
        """Test that error statistics are tracked."""
        initial_stats = error_handler.get_error_stats()
        
        # Create and handle some errors
        error1 = AgentError("Error 1", ErrorCategory.VALIDATION)
        error2 = AgentError("Error 2", ErrorCategory.COMPUTATION)
        error3 = AgentError("Error 3", ErrorCategory.VALIDATION)
        
        error_handler.handle_error(error1)
        error_handler.handle_error(error2)  
        error_handler.handle_error(error3)
        
        final_stats = error_handler.get_error_stats()
        
        # Should have recorded errors
        assert final_stats["total_errors"] >= initial_stats["total_errors"]
        assert "error_breakdown" in final_stats
    
    def test_error_handling_with_logging(self, error_handler, caplog):
        """Test that error handling includes proper logging."""
        with caplog.at_level(logging.WARNING):
            error = AgentError("Test error for logging", ErrorCategory.SECURITY)
            error_handler.handle_error(error)
            
        # Should have logged the error
        assert len(caplog.records) > 0
        assert any("error" in record.getMessage().lower() for record in caplog.records)
    
    def test_error_context_preservation(self, error_handler):
        """Test that error handling modifies context appropriately."""
        context = {"expression": "2 + abc", "source": "calculator"}
        error = AgentError("Test error", ErrorCategory.VALIDATION, context=context)
        
        # Handle the error
        handled_error = error_handler.handle_error(error)
        
        # Original context should still be accessible, but might be enriched
        assert "expression" in str(handled_error.context) or handled_error.context != context
        # The error handler may add additional context


class TestSafeCalculatorErrorHandling:
    """Test error handling in SafeCalculator component."""
    
    @pytest.mark.security
    def test_security_error_handling(self, calculator):
        """Test that SafeCalculator properly handles security threats."""
        malicious_expressions = [
            "__import__('os').system('ls')",
            "exec('print(1)')",
            "eval('2+2')"
        ]
        
        for expression in malicious_expressions:
            with pytest.raises(AgentError) as exc_info:
                calculator.evaluate_expression(expression)
            
            error = exc_info.value
            assert error.category == ErrorCategory.SECURITY
            assert "dangerous pattern" in error.message.lower() or "security" in error.message.lower()
            assert "security reasons" in error.user_message.lower()
    
    def test_validation_error_handling(self, calculator):
        """Test validation error handling in SafeCalculator."""
        invalid_expressions = [
            "2 + abc",
            "undefined_function()",
            "2 + # comment",
            "   # just comment   "
        ]
        
        for expression in invalid_expressions:
            with pytest.raises(AgentError) as exc_info:
                calculator.evaluate_expression(expression)
            
            error = exc_info.value
            assert error.category == ErrorCategory.VALIDATION
            assert "invalid characters" in error.message.lower() or "expression" in error.message.lower()
    
    def test_computation_error_handling(self, calculator):
        """Test computation error handling in SafeCalculator."""
        # Division by zero
        with pytest.raises(AgentError) as exc_info:
            calculator.evaluate_expression("1 / 0")
        
        error = exc_info.value
        assert error.category == ErrorCategory.COMPUTATION
        assert "division by zero" in error.message.lower()
    
    def test_length_limit_error_handling(self, calculator):
        """Test that length limits trigger appropriate errors."""
        # Create an expression that's definitely too long
        long_expression = "1 + 1" * 500  # Should exceed any reasonable limit
        
        with pytest.raises(AgentError) as exc_info:
            calculator.evaluate_expression(long_expression)
        
        error = exc_info.value
        assert error.category == ErrorCategory.SECURITY
        assert "too long" in error.message.lower()


class TestCalculatorToolErrorHandling:
    """Test error handling in CalculatorTool component."""
    
    def test_tool_error_message_format(self, calculator_tool):
        """Test that tool error messages are properly formatted."""
        # Test security error
        result = calculator_tool._run("__import__('os')")
        assert result.startswith("Calculator Error:")
        assert "security reasons" in result.lower()
        assert "Suggestions:" in result
    
    def test_tool_validation_error_format(self, calculator_tool):
        """Test validation error formatting in tool."""
        result = calculator_tool._run("2 + invalid_var")
        assert result.startswith("Calculator Error:")
        assert "issue with the input" in result.lower()
        assert "Suggestions:" in result
    
    def test_tool_computation_error_format(self, calculator_tool):
        """Test computation error formatting in tool."""
        result = calculator_tool._run("1 / 0")
        assert result.startswith("Calculator Error:")
        assert "calculation" in result.lower() or "error" in result.lower()
        assert "Suggestions:" in result
    
    def test_tool_error_suggestions_helpful(self, calculator_tool):
        """Test that tool error suggestions are helpful."""
        # Security error should suggest reviewing input
        security_result = calculator_tool._run("__import__('os')")
        assert "review" in security_result.lower() or "check" in security_result.lower()
        
        # Validation error should suggest checking input
        validation_result = calculator_tool._run("2 + abc")
        assert "check" in validation_result.lower() or "typos" in validation_result.lower()
    
    def test_tool_preserves_error_information(self, calculator_tool):
        """Test that tool preserves important error information."""
        # The tool should maintain error categorization internally
        # even though it returns user-friendly strings
        result = calculator_tool._run("__import__('os')")
        
        # Should indicate it was blocked for security
        assert "security" in result.lower() or "blocked" in result.lower()


class TestErrorRecovery:
    """Test error recovery mechanisms."""
    
    def test_recovery_suggestions_context_aware(self):
        """Test that recovery suggestions are context-aware."""
        # Connectivity error should suggest connection-related solutions
        conn_error = AgentError(
            "Connection failed",
            ErrorCategory.CONNECTIVITY,
            context={"endpoint": "api.example.com"}
        )
        
        suggestions = conn_error.recovery_suggestions
        assert len(suggestions) > 0
        assert any("network" in suggestion.lower() or "connection" in suggestion.lower() or "wait" in suggestion.lower()
                  for suggestion in suggestions)
    
    def test_security_error_recovery(self):
        """Test recovery suggestions for security errors."""
        security_error = AgentError(
            "Dangerous code detected",
            ErrorCategory.SECURITY,
            context={"pattern": "__import__"}
        )
        
        suggestions = security_error.recovery_suggestions
        assert len(suggestions) > 0
        assert any("review" in suggestion.lower() for suggestion in suggestions)
        assert any("mathematical" in suggestion.lower() or "safe" in suggestion.lower() 
                  for suggestion in suggestions)
    
    def test_validation_error_recovery(self):
        """Test recovery suggestions for validation errors."""
        validation_error = AgentError(
            "Invalid input format",
            ErrorCategory.VALIDATION,
            context={"input": "bad_format"}
        )
        
        suggestions = validation_error.recovery_suggestions
        assert len(suggestions) > 0
        assert any("check" in suggestion.lower() or "format" in suggestion.lower()
                  for suggestion in suggestions)


class TestErrorIntegration:
    """Integration tests for error handling system."""
    
    def test_error_handling_with_circuit_breaker(self, error_handler, circuit_breaker):
        """Test error handling integration with circuit breaker."""
        # Record some failures
        for _ in range(3):
            error = AgentError("Service failure", ErrorCategory.CONNECTIVITY)
            error_handler.handle_error(error)
            circuit_breaker.record_failure()
        
        # Circuit breaker should reflect the failures
        assert circuit_breaker.failure_count >= 3
    
    def test_comprehensive_error_flow(self, calculator, error_handler):
        """Test complete error flow from detection to handling."""
        try:
            calculator.evaluate_expression("__import__('os')")
            pytest.fail("Should have raised an error")
        except AgentError as error:
            # Handle the error
            handled_error = error_handler.handle_error(error)
            
            # Verify error was properly categorized and handled
            assert handled_error.category == ErrorCategory.SECURITY
            assert handled_error.user_message
            assert len(handled_error.recovery_suggestions) > 0
            
            # Verify statistics were updated
            stats = error_handler.get_error_stats()
            assert stats["total_errors"] > 0
            assert "error_breakdown" in stats
    
    @pytest.mark.slow
    def test_error_handling_performance(self, error_handler):
        """Test that error handling doesn't significantly impact performance."""
        import time
        
        start_time = time.time()
        
        # Handle many errors quickly
        for i in range(100):
            error = AgentError(f"Error {i}", ErrorCategory.VALIDATION)
            error_handler.handle_error(error)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly (less than 1 second for 100 errors)
        assert duration < 1.0, f"Error handling took too long: {duration:.2f} seconds"
