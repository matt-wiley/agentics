#!/usr/bin/env python3
"""
Test suite for comprehensive error handling system (Task 2.2).
"""

import sys
import time
import logging
from unittest.mock import patch, MagicMock

# Add the current directory to Python path
sys.path.append('.')

# Import our enhanced error handling components
from simplest_agent import (
    ErrorCategory, AgentError, ErrorHandler, SafeCalculator,
    CalculatorTool, error_handler
)

# Configure logging to see error handling in action
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_error_classification():
    """Test error classification system."""
    print("📋 Testing Error Classification...")
    
    handler = ErrorHandler()
    
    # Test connectivity errors
    conn_error = Exception("Connection refused to server")
    assert handler.classify_error(conn_error) == ErrorCategory.CONNECTIVITY
    print("✅ Connection errors classified correctly")
    
    # Test validation errors
    val_error = Exception("Invalid syntax in expression")
    assert handler.classify_error(val_error) == ErrorCategory.VALIDATION
    print("✅ Validation errors classified correctly")
    
    # Test computation errors
    comp_error = Exception("Division by zero error")
    assert handler.classify_error(comp_error) == ErrorCategory.COMPUTATION
    print("✅ Computation errors classified correctly")
    
    # Test security errors
    sec_error = Exception("Dangerous pattern blocked")
    assert handler.classify_error(sec_error) == ErrorCategory.SECURITY
    print("✅ Security errors classified correctly")


def test_agent_error_creation():
    """Test AgentError creation and user message generation."""
    print("\n🏗️ Testing AgentError Creation...")
    
    # Test connectivity error
    error = AgentError(
        "Connection timeout", 
        ErrorCategory.CONNECTIVITY,
        context={"server": "ollama", "timeout": 30}
    )
    
    assert "trouble connecting" in error.user_message.lower()
    assert "wait a moment" in error.recovery_suggestions[0].lower()
    print("✅ Connectivity error messages are user-friendly")
    
    # Test validation error
    val_error = AgentError(
        "Invalid expression format",
        ErrorCategory.VALIDATION,
        context={"expression": "bad_input"}
    )
    
    assert "issue with the input" in val_error.user_message.lower()
    assert "check and try again" in val_error.user_message.lower()
    print("✅ Validation error messages provide clear guidance")
    
    # Test error serialization
    error_dict = error.to_dict()
    assert "error_id" in error_dict
    assert "category" in error_dict
    assert error_dict["category"] == "connectivity"
    print("✅ Error serialization works correctly")


def test_safe_calculator_enhanced_errors():
    """Test SafeCalculator with enhanced error handling."""
    print("\n🧮 Testing SafeCalculator Enhanced Errors...")
    
    calc = SafeCalculator()
    
    # Test security error
    try:
        calc.evaluate_expression("__import__('os').system('ls')")
        assert False, "Should have raised security error"
    except AgentError as e:
        assert e.category == ErrorCategory.SECURITY
        assert "dangerous pattern" in e.message.lower()
        assert "security reasons" in e.user_message.lower()
        print("✅ Security patterns blocked with clear messaging")
    
    # Test validation error
    try:
        calc.evaluate_expression("2 + abc")
        assert False, "Should have raised validation error"
    except AgentError as e:
        assert e.category == ErrorCategory.VALIDATION
        assert "invalid characters" in e.message.lower()
        print("✅ Invalid characters caught with helpful context")
    
    # Test computation error
    try:
        calc.evaluate_expression("1 / 0")
        assert False, "Should have raised computation error"
    except AgentError as e:
        assert e.category == ErrorCategory.COMPUTATION
        assert "division by zero" in e.message.lower()
        print("✅ Division by zero handled with proper categorization")
    
    # Test length limit
    try:
        calc.evaluate_expression("1 + 1" * 300)  # Definitely over 1000 chars
        assert False, "Should have raised security error"
    except AgentError as e:
        assert e.category == ErrorCategory.SECURITY
        assert "too long" in e.message.lower()
        print("✅ Length limits enforced for security")


def test_calculator_tool_error_handling():
    """Test CalculatorTool with enhanced error responses."""
    print("\n🔧 Testing CalculatorTool Error Handling...")
    
    calc_tool = CalculatorTool()
    
    # Test normal operation
    result = calc_tool._run("2 + 3 * 4")
    assert "14" in result
    print("✅ Normal calculations work correctly")
    
    # Test security error handling
    result = calc_tool._run("eval('2+2')")
    assert "Calculator Error:" in result
    assert "security reasons" in result.lower()
    assert "Suggestions:" in result
    print("✅ Security errors provide user-friendly responses")
    
    # Test validation error handling  
    result = calc_tool._run("2 + invalid")
    assert "Calculator Error:" in result
    assert "input provided" in result.lower()
    print("✅ Validation errors provide helpful guidance")
    
    # Test computation error handling
    result = calc_tool._run("1 / 0")
    assert "Calculator Error:" in result
    assert "division by zero" in result.lower() or "processing your calculation" in result.lower()
    print("✅ Computation errors handled gracefully")


def test_error_handler_statistics():
    """Test error statistics tracking."""
    print("\n📊 Testing Error Statistics...")
    
    handler = ErrorHandler()
    
    # Generate some test errors
    for i in range(3):
        try:
            raise Exception("Connection timeout")
        except Exception as e:
            handler.handle_error(e, operation="test_conn")
    
    for i in range(2):
        try:
            raise ValueError("Invalid input")
        except Exception as e:
            handler.handle_error(e, operation="test_val")
    
    stats = handler.get_error_stats()
    assert stats["total_errors"] == 5
    assert len(stats["error_breakdown"]) >= 2
    assert stats["most_common"] is not None
    print(f"✅ Error statistics tracked correctly: {stats['total_errors']} total errors")


def test_error_context_preservation():
    """Test that error context is preserved through handling."""
    print("\n📝 Testing Error Context Preservation...")
    
    # Test context preservation in AgentError
    original_context = {"user_input": "test", "operation": "demo"}
    error = AgentError(
        "Test error",
        ErrorCategory.VALIDATION,
        context=original_context
    )
    
    assert error.context["user_input"] == "test"
    assert error.context["operation"] == "demo"
    print("✅ Error context preserved in AgentError")
    
    # Test context enrichment in ErrorHandler
    handler = ErrorHandler()
    try:
        raise Exception("Test exception")
    except Exception as e:
        handled = handler.handle_error(e, context={"test": "value"}, operation="test_op")
        assert handled.context["test"] == "value"
        assert handled.context["operation"] == "test_op"
        assert "error_type" in handled.context
        print("✅ Error context enriched by ErrorHandler")


def test_recovery_suggestions():
    """Test context-aware recovery suggestions."""
    print("\n💡 Testing Recovery Suggestions...")
    
    categories_to_test = [
        (ErrorCategory.CONNECTIVITY, "wait a moment"),
        (ErrorCategory.VALIDATION, "check your input"),
        (ErrorCategory.SECURITY, "avoid using system commands"),
        (ErrorCategory.COMPUTATION, "try breaking"),
        (ErrorCategory.TIMEOUT, "simpler version")
    ]
    
    for category, expected_phrase in categories_to_test:
        error = AgentError("Test error", category)
        suggestions = " ".join(error.recovery_suggestions).lower()
        assert expected_phrase in suggestions, f"Expected '{expected_phrase}' in suggestions for {category}"
        print(f"✅ {category.value} errors have appropriate recovery suggestions")


def test_logging_levels():
    """Test that appropriate logging levels are used."""
    print("\n📝 Testing Logging Levels...")
    
    handler = ErrorHandler()
    
    # Test that security errors get ERROR level
    security_level = handler._get_log_level(ErrorCategory.SECURITY)
    assert security_level == logging.ERROR
    print("✅ Security errors logged at ERROR level")
    
    # Test that validation errors get INFO level
    validation_level = handler._get_log_level(ErrorCategory.VALIDATION)
    assert validation_level == logging.INFO
    print("✅ Validation errors logged at INFO level")
    
    # Test that connectivity errors get WARNING level
    conn_level = handler._get_log_level(ErrorCategory.CONNECTIVITY)
    assert conn_level == logging.WARNING
    print("✅ Connectivity errors logged at WARNING level")


def main():
    """Run all error handling tests."""
    print("🧪 Starting Comprehensive Error Handling Tests")
    print("=" * 60)
    
    try:
        test_error_classification()
        test_agent_error_creation()
        test_safe_calculator_enhanced_errors()
        test_calculator_tool_error_handling()
        test_error_handler_statistics()
        test_error_context_preservation()
        test_recovery_suggestions()
        test_logging_levels()
        
        print("\n" + "=" * 60)
        print("🎉 All comprehensive error handling tests passed!")
        print("\n📋 Test Summary:")
        print("• Error classification and categorization ✅")
        print("• User-friendly error messages ✅") 
        print("• Context-aware recovery suggestions ✅")
        print("• Security error handling ✅")
        print("• Error statistics and monitoring ✅")
        print("• Structured logging with appropriate levels ✅")
        print("• Context preservation throughout error handling ✅")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
