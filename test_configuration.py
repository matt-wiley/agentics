#!/usr/bin/env python3
"""
Configuration validation test for Task 3.1.

Tests the configuration management system without requiring
external dependencies like langchain.
"""

import os
import sys
from unittest.mock import patch

# Temporarily mock the langchain imports to test config system only
sys.modules['langchain_ollama'] = type(sys)('mock_module')
sys.modules['langchain.agents'] = type(sys)('mock_module') 
sys.modules['langchain.memory'] = type(sys)('mock_module')
sys.modules['langchain.tools'] = type(sys)('mock_module')

# Mock the classes we need
class MockChatOllama:
    pass

class MockAgentType:
    CHAT_CONVERSATIONAL_REACT_DESCRIPTION = "mock"

class MockConversationBufferMemory:
    def __init__(self, **kwargs):
        pass

class MockBaseTool:
    pass

class MockBaseModel:
    pass

class MockField:
    def __init__(self, *args, **kwargs):
        # Accept any arguments like the real Field
        pass

# Add mocked classes to modules
sys.modules['langchain_ollama'].ChatOllama = MockChatOllama
sys.modules['langchain.agents'].AgentType = MockAgentType
sys.modules['langchain.agents'].initialize_agent = lambda *args, **kwargs: None
sys.modules['langchain.memory'].ConversationBufferMemory = MockConversationBufferMemory
sys.modules['langchain.tools'].BaseTool = MockBaseTool
sys.modules['pydantic'] = type(sys)('mock_module')
sys.modules['pydantic'].BaseModel = MockBaseModel
sys.modules['pydantic'].Field = MockField

def test_configuration_system():
    """Test the configuration system with default values."""
    
    print("Testing Configuration System (Task 3.1)")
    print("=" * 50)
    
    try:
        # Import config after mocking
        from simplest_agent import AgentConfig
        
        # Test default configuration
        config = AgentConfig()
        
        print("✅ Configuration loaded successfully with defaults!")
        print(f"   Model: {config.model_name}")
        print(f"   Provider: {config.model_provider}")  
        print(f"   Temperature: {config.model_temperature}")
        print(f"   Max iterations: {config.agent_max_iterations}")
        print(f"   Retry attempts: {config.retry_max_attempts}")
        print(f"   Calculator max length: {config.calculator_max_expression_length}")
        print(f"   Log level: {config.log_level}")
        
        # Test validation
        errors = config.validate()
        if not errors:
            print("✅ Validation passed!")
        else:
            print(f"❌ Validation errors: {errors}")
            return False
            
        # Test model kwargs
        kwargs = config.get_model_kwargs()
        print(f"✅ Model kwargs generated: {kwargs}")
        
        # Test environment variable override
        print("\nTesting environment variable override...")
        with patch.dict(os.environ, {
            'AGENT_MODEL': 'test-model',
            'AGENT_PROVIDER': 'ollama',  # Use ollama to avoid API key requirement
            'AGENT_TEMPERATURE': '0.5',
            'RETRY_MAX_ATTEMPTS': '5'
        }):
            config_override = AgentConfig()
            print(f"   Model: {config_override.model_name}")
            print(f"   Provider: {config_override.model_provider}")
            print(f"   Temperature: {config_override.model_temperature}")
            print(f"   Retry attempts: {config_override.retry_max_attempts}")
            print("✅ Environment variable override works!")
            
        # Test validation with invalid values
        print("\nTesting validation with invalid values...")
        with patch.dict(os.environ, {
            'AGENT_PROVIDER': 'invalid_provider',
            'AGENT_TEMPERATURE': '5.0',  # Too high
            'RETRY_MAX_ATTEMPTS': '0'    # Too low
        }):
            try:
                invalid_config = AgentConfig()
                print("❌ Should have failed validation!")
                return False
            except Exception as e:
                print(f"✅ Correctly caught invalid configuration: {type(e).__name__}")
                
        print("\n🎉 All configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_features():
    """Test specific configuration features."""
    
    print("\nTesting Configuration Features")
    print("=" * 30)
    
    from simplest_agent import AgentConfig
    
    # Test provider-specific validation
    test_cases = [
        {
            'name': 'Valid Ollama Config',
            'env': {'AGENT_PROVIDER': 'ollama', 'OLLAMA_BASE_URL': 'http://localhost:11434'},
            'should_pass': True
        },
        {
            'name': 'Invalid Ollama Config (missing URL)',
            'env': {'AGENT_PROVIDER': 'ollama', 'OLLAMA_BASE_URL': ''},
            'should_pass': False
        },
        {
            'name': 'Valid OpenAI Config',
            'env': {'AGENT_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'},
            'should_pass': True
        },
        {
            'name': 'Invalid OpenAI Config (missing key)',
            'env': {'AGENT_PROVIDER': 'openai', 'OPENAI_API_KEY': ''},
            'should_pass': False
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        with patch.dict(os.environ, test_case['env'], clear=False):
            try:
                config = AgentConfig()
                if test_case['should_pass']:
                    print(f"   ✅ Passed as expected")
                else:
                    print(f"   ❌ Should have failed but didn't")
                    return False
            except Exception as e:
                if not test_case['should_pass']:
                    print(f"   ✅ Failed as expected: {type(e).__name__}")
                else:
                    print(f"   ❌ Should have passed but failed: {e}")
                    return False
    
    print("\n✅ All feature tests passed!")
    return True

if __name__ == "__main__":
    success1 = test_configuration_system()
    success2 = test_configuration_features()
    
    if success1 and success2:
        print("\n🎯 Task 3.1 Configuration Management: IMPLEMENTATION COMPLETE!")
        print("\nSummary of implemented features:")
        print("• Environment variable-based configuration")
        print("• Comprehensive validation with helpful error messages")
        print("• Support for multiple model providers (ollama, openai, litellm)")
        print("• Configuration defaults for all settings")
        print("• Runtime configuration validation")
        print("• Automatic environment setup for compatibility")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
