"""Unit tests for SafeCalculator and CalculatorTool components."""
import pytest
from simplest_agent import SafeCalculator, CalculatorTool, AgentError, ErrorCategory


class TestSafeCalculator:
    """Test the SafeCalculator class."""
    
    def test_basic_arithmetic_operations(self, calculator):
        """Test basic arithmetic operations work correctly."""
        test_cases = [
            ("2 + 3", 5),
            ("10 - 4", 6),
            ("6 * 7", 42),
            ("15 / 3", 5.0),
            ("2 ** 3", 8),
            ("10 % 3", 1),
            ("-5", -5),
            ("+5", 5),
        ]
        
        for expression, expected in test_cases:
            result = calculator.evaluate_expression(expression)
            assert result == expected, f"Failed for {expression}: got {result}, expected {expected}"
    
    def test_complex_expressions(self, calculator):
        """Test complex mathematical expressions with parentheses and precedence."""
        test_cases = [
            ("(2 + 3) * 4", 20),
            ("10 + 5 * 2", 20),  # Precedence: multiplication before addition
            ("(10 + 5) * 2", 30), # Parentheses override precedence
            ("((1 + 2) * 3) + 4", 13),
            ("2 + 3 * 4 - 1", 13),  # Mixed operations
        ]
        
        for expression, expected in test_cases:
            result = calculator.evaluate_expression(expression)
            assert result == expected, f"Failed for {expression}: got {result}, expected {expected}"
    
    def test_builtin_functions(self, calculator):
        """Test that only basic arithmetic operations are supported."""
        # The current SafeCalculator only supports basic arithmetic
        # and does NOT support functions like abs, max, min, etc.
        unsupported_functions = [
            "abs(-5)",
            "max(1, 2, 3)",
            "min(1, 2, 3)",
            "round(3.14159, 2)",
            "pow(2, 3)",
            "sqrt(16)",
        ]
        
        for expression in unsupported_functions:
            with pytest.raises((ValueError, AgentError)) as exc_info:
                calculator.evaluate_expression(expression)
            
            # Check that it's a validation error for invalid characters
            error_message = str(exc_info.value).lower()
            assert "invalid characters" in error_message
    
    @pytest.mark.security
    def test_security_patterns_blocked(self, calculator):
        """Test that dangerous security patterns are blocked."""
        malicious_expressions = [
            "__import__('os').system('ls')",
            "exec('print(1)')",
            "eval('2+2')",
            "open('/etc/passwd')",
            "compile('print(1)', '', 'exec')",
        ]
        
        for expression in malicious_expressions:
            with pytest.raises((ValueError, AgentError)) as exc_info:
                calculator.evaluate_expression(expression)
            
            # Check that the error message indicates security blocking
            error_message = str(exc_info.value).lower()
            assert any(keyword in error_message for keyword in ['security', 'dangerous', 'pattern']), \
                f"Security error message should mention blocking reason for: {expression}"
        
        # Test expressions that are caught by character validation
        # (these contain letters that are blocked)
        character_validation_expressions = [
            "globals()",
            "locals()", 
            "vars()",
            "dir()",
            "getattr(object, 'attr')",
            "setattr(object, 'attr', 'value')",
        ]
        
        for expression in character_validation_expressions:
            with pytest.raises((ValueError, AgentError)) as exc_info:
                calculator.evaluate_expression(expression)
            
            # These should fail due to invalid characters
            error_message = str(exc_info.value).lower()
            assert "invalid characters" in error_message, \
                f"Character validation error expected for: {expression}"
        
        # Test __builtins__ which is caught by pattern detection (not character validation)
        with pytest.raises((ValueError, AgentError)) as exc_info:
            calculator.evaluate_expression("__builtins__")
        
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['security', 'dangerous', 'pattern']), \
            f"Security error message should mention blocking reason for: __builtins__"
    
    @pytest.mark.security 
    def test_dangerous_character_patterns(self, calculator):
        """Test that expressions with dangerous character patterns are rejected."""
        dangerous_patterns = [
            "2 & 3",   # Bitwise operations
            "2 | 3",   # Bitwise operations  
            "2 ^ 3",   # Bitwise XOR
            "~2",      # Bitwise NOT
            "2 << 1",  # Bit shift
            "2 >> 1",  # Bit shift
        ]
        
        for expression in dangerous_patterns:
            with pytest.raises((ValueError, AgentError)):
                calculator.evaluate_expression(expression)
    
    def test_validation_errors(self, calculator):
        """Test that invalid expressions raise appropriate validation errors."""
        invalid_expressions = [
            "",           # Empty expression
            "   ",        # Whitespace only
            "2 +",        # Incomplete expression
            "* 5",        # Invalid start
            "2 + a",      # Undefined variable
            "hello",      # Non-mathematical text
            "2 + 3)",     # Unbalanced parentheses
            "((2 + 3",    # Unbalanced parentheses
        ]
        
        for expression in invalid_expressions:
            with pytest.raises((ValueError, AgentError, SyntaxError)):
                calculator.evaluate_expression(expression)
    
    def test_computation_errors(self, calculator):
        """Test handling of mathematical computation errors."""
        # Test division by zero
        with pytest.raises((ZeroDivisionError, AgentError)):
            calculator.evaluate_expression("1 / 0")
        
        # Test very large results (if power limits are implemented)
        with pytest.raises((OverflowError, AgentError, ValueError)):
            calculator.evaluate_expression("2 ** 1000")
    
    def test_length_validation(self, calculator):
        """Test that overly long expressions are rejected."""
        # Create a very long expression
        long_expression = " + ".join(["1"] * 500)  # Should exceed length limits
        
        with pytest.raises((ValueError, AgentError)) as exc_info:
            calculator.evaluate_expression(long_expression)
        
        error_message = str(exc_info.value).lower()
        assert 'length' in error_message or 'long' in error_message
    
    @pytest.mark.parametrize("expression,expected", [
        ("2 + 2", 4),
        ("5 * 6", 30),
        ("10 / 2", 5.0),
        ("3 ** 2", 9),
        ("(1 + 2) * 3", 9),
    ])
    def test_parametrized_expressions(self, calculator, expression, expected):
        """Test expressions using pytest parametrization (only basic operations)."""
        result = calculator.evaluate_expression(expression)
        assert result == expected


class TestCalculatorTool:
    """Test the CalculatorTool LangChain integration."""
    
    def test_tool_initialization(self):
        """Test that CalculatorTool initializes correctly."""
        tool = CalculatorTool()
        assert tool.name == "calculator"
        assert "math" in tool.description.lower()
    
    def test_valid_calculations(self, calculator_tool):
        """Test CalculatorTool with valid mathematical expressions."""
        test_cases = [
            ("5 + 3", "8"),
            ("12 / 4", "3.0"),
            ("2 ** 4", "16"),
            ("(1 + 2) * 3", "9"),
        ]
        
        for expression, expected in test_cases:
            result = calculator_tool._run(expression)
            assert result == expected, f"Failed for {expression}: got {result}, expected {expected}"
    
    @pytest.mark.security
    def test_security_error_handling(self, calculator_tool):
        """Test that CalculatorTool handles security errors gracefully."""
        malicious_expressions = [
            "__import__('os')",
            "exec('print(1)')",
            "eval('2+2')",
        ]
        
        for expression in malicious_expressions:
            result = calculator_tool._run(expression)
            assert result.startswith("Calculator Error:"), f"Security error should start with 'Calculator Error:' for {expression}"
            assert "security" in result.lower() or "dangerous" in result.lower()
    
    def test_validation_error_handling(self, calculator_tool):
        """Test that CalculatorTool handles validation errors gracefully.""" 
        invalid_expressions = [
            "2 + invalid_var",
            "undefined_function()",
            "2 +",
        ]
        
        for expression in invalid_expressions:
            result = calculator_tool._run(expression)
            assert result.startswith("Calculator Error:"), f"Validation error should start with 'Calculator Error:' for {expression}"
    
    def test_computation_error_handling(self, calculator_tool):
        """Test that CalculatorTool handles computation errors gracefully."""
        result = calculator_tool._run("1 / 0")
        assert result.startswith("Calculator Error:"), "Division by zero should return error message"
        assert "calculation" in result.lower() or "error" in result.lower()
    
    def test_error_messages_user_friendly(self, calculator_tool):
        """Test that error messages are user-friendly and informative."""
        # Test security error
        result = calculator_tool._run("__import__('os')")
        assert "Calculator Error:" in result
        assert "security reasons" in result.lower() or "dangerous pattern" in result.lower()
        
        # Test validation error
        result = calculator_tool._run("2 + abc")
        assert "Calculator Error:" in result
        assert any(word in result.lower() for word in ['issue', 'input', 'provided'])


class TestCalculatorIntegration:
    """Integration tests for Calculator components."""
    
    def test_calculator_tool_uses_safe_calculator(self, calculator_tool):
        """Test that CalculatorTool uses SafeCalculator internally."""
        # This test verifies the integration between the components
        result = calculator_tool._run("2 + 3")
        assert result == "5"
        
        # Test that security is enforced through the integration
        result = calculator_tool._run("__import__('os')")
        assert result.startswith("Calculator Error:")
    
    @pytest.mark.slow
    def test_performance_with_complex_expressions(self, calculator_tool):
        """Test performance with complex but valid expressions."""
        import time
        
        complex_expression = "((1 + 2) * 3 + (4 * 5)) / ((6 + 7) - 8)"
        
        start_time = time.time()
        result = calculator_tool._run(complex_expression)
        end_time = time.time()
        
        # Should complete quickly (less than 1 second)
        assert end_time - start_time < 1.0
        # Should return a valid result
        assert not result.startswith("Error:")
        
    def test_edge_cases(self, calculator_tool):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            ("0", "0"),
            ("0.0", "0.0"), 
            ("-0", "0"),
            ("1.0", "1.0"),
            ("0.1 + 0.2", "0.30000000000000004"),  # Floating point precision
        ]
        
        for expression, expected in edge_cases:
            result = calculator_tool._run(expression)
            assert result == expected, f"Edge case failed for {expression}"
