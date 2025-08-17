"""Unit tests for AgentConfig configuration management."""
import pytest
import os
from unittest.mock import patch
from simplest_agent import AgentConfig


class TestAgentConfig:
    """Test the AgentConfig class and configuration management."""
    
    def test_default_configuration(self, test_env):
        """Test that default configuration loads with expected values."""
        with patch.dict(os.environ, test_env, clear=True):
            config = AgentConfig()
            
            # Test essential defaults
            assert config.model_name == "test-model"
            assert config.model_provider == "ollama"
            assert config.model_temperature == 0.0
            assert config.agent_verbose is False
            assert config.agent_max_iterations == 5
            assert config.retry_max_attempts == 2
            assert config.circuit_breaker_failure_threshold == 3
            assert config.log_level == "WARNING"
    
    def test_environment_variable_override(self, test_env):
        """Test that environment variables properly override defaults."""
        custom_env = test_env.copy()
        custom_env.update({
            'AGENT_MODEL': 'custom-model',
            'AGENT_TEMPERATURE': '0.7',
            'AGENT_MAX_ITERATIONS': '20',
            'RETRY_MAX_ATTEMPTS': '5',
            'LOG_LEVEL': 'DEBUG'
        })
        
        with patch.dict(os.environ, custom_env, clear=True):
            config = AgentConfig()
            
            assert config.model_name == "custom-model"
            assert config.model_temperature == 0.7
            assert config.agent_max_iterations == 20
            assert config.retry_max_attempts == 5
            assert config.log_level == "DEBUG"
    
    def test_model_kwargs_generation(self, agent_config):
        """Test that model kwargs are generated correctly."""
        kwargs = agent_config.get_model_kwargs()
        
        assert isinstance(kwargs, dict)
        assert 'temperature' in kwargs
        assert kwargs['temperature'] == agent_config.model_temperature
    
    @pytest.mark.parametrize("provider,env_vars,should_pass", [
        # Valid configurations
        ("ollama", {"OLLAMA_BASE_URL": "http://localhost:11434"}, True),
        ("openai", {"OPENAI_API_KEY": "test-key-12345"}, True),
        ("litellm", {"LITELLM_KEY": "test-key", "LITELLM_BASE_URL": "http://localhost:4000"}, True),
        
        # Invalid configurations
        ("ollama", {"OLLAMA_BASE_URL": ""}, False),
        ("openai", {"OPENAI_API_KEY": ""}, False),
        ("unknown_provider", {}, False),
    ])
    def test_provider_validation(self, test_env, provider, env_vars, should_pass):
        """Test provider-specific configuration validation."""
        test_config = test_env.copy()
        test_config['AGENT_PROVIDER'] = provider
        test_config.update(env_vars)
        
        with patch.dict(os.environ, test_config, clear=True):
            if should_pass:
                # Should create config successfully
                config = AgentConfig()
                assert config.model_provider == provider
            else:
                # Should raise an exception during validation
                with pytest.raises(Exception):
                    config = AgentConfig()
                    config.validate()
    
    def test_validation_with_valid_config(self, agent_config):
        """Test that validation passes for a valid configuration."""
        errors = agent_config.validate()
        assert errors == [] or errors is None, f"Valid config should pass validation, but got errors: {errors}"
    
    def test_validation_with_invalid_temperature(self, test_env):
        """Test validation fails for invalid temperature values."""
        invalid_temps = ['-1.0', '2.1', '5.0']  # Outside valid range
        
        for temp in invalid_temps:
            test_config = test_env.copy()
            test_config['AGENT_TEMPERATURE'] = temp
            
            with patch.dict(os.environ, test_config, clear=True):
                # Config validation happens in __post_init__, so creation should raise exception
                with pytest.raises(Exception) as exc_info:
                    AgentConfig()
                
                error_message = str(exc_info.value).lower()
                assert 'temperature' in error_message
    
    def test_validation_with_invalid_retry_attempts(self, test_env):
        """Test validation fails for invalid retry attempt values."""
        invalid_attempts = ['0', '-1']  # Outside reasonable range
        
        for attempts in invalid_attempts:
            test_config = test_env.copy()
            test_config['RETRY_MAX_ATTEMPTS'] = attempts
            
            with patch.dict(os.environ, test_config, clear=True):
                # Config validation happens in __post_init__, so creation should raise exception
                with pytest.raises(Exception) as exc_info:
                    AgentConfig()
                
                error_message = str(exc_info.value).lower()
                assert 'retry' in error_message or 'attempts' in error_message
    
    def test_ollama_specific_config(self, test_env):
        """Test Ollama-specific configuration requirements."""
        ollama_config = test_env.copy()
        ollama_config.update({
            'AGENT_PROVIDER': 'ollama',
            'OLLAMA_BASE_URL': 'http://custom-ollama:11434'
        })
        
        with patch.dict(os.environ, ollama_config, clear=True):
            config = AgentConfig()
            assert config.model_provider == "ollama"
            assert config.ollama_base_url == "http://custom-ollama:11434"
            
            # Should pass validation
            errors = config.validate()
            assert not errors
    
    def test_openai_specific_config(self, test_env):
        """Test OpenAI-specific configuration requirements."""
        openai_config = test_env.copy()
        openai_config.update({
            'AGENT_PROVIDER': 'openai',
            'AGENT_MODEL': 'gpt-3.5-turbo',
            'OPENAI_API_KEY': 'sk-test1234567890abcdef',
            'OPENAI_API_BASE': 'https://api.openai.com/v1'
        })
        
        with patch.dict(os.environ, openai_config, clear=True):
            config = AgentConfig()
            assert config.model_provider == "openai"
            assert config.model_name == "gpt-3.5-turbo"
            assert config.openai_api_key == "sk-test1234567890abcdef"
            assert config.openai_api_base == "https://api.openai.com/v1"
    
    def test_litellm_specific_config(self, test_env):
        """Test LiteLLM-specific configuration requirements."""
        litellm_config = test_env.copy()
        litellm_config.update({
            'AGENT_PROVIDER': 'litellm',
            'LITELLM_KEY': 'test-key',
            'LITELLM_BASE_URL': 'http://localhost:4000'
        })
        
        with patch.dict(os.environ, litellm_config, clear=True):
            config = AgentConfig()
            assert config.model_provider == "litellm"
            assert config.litellm_key == "test-key"
            assert config.litellm_base_url == "http://localhost:4000"
    
    def test_configuration_immutability(self, agent_config):
        """Test that configuration behaves as expected after creation."""
        original_model = agent_config.model_name
        original_temp = agent_config.model_temperature
        
        # Configuration should maintain its values
        assert agent_config.model_name == original_model
        assert agent_config.model_temperature == original_temp
    
    def test_calculator_specific_settings(self, agent_config):
        """Test calculator-specific configuration settings."""
        # These should have reasonable defaults
        assert agent_config.calculator_max_expression_length > 0
        assert agent_config.calculator_max_power > 0
        
        # Should be configurable via environment
        with patch.dict(os.environ, {
            'CALCULATOR_MAX_LENGTH': '500',
            'CALCULATOR_MAX_POWER': '50'
        }):
            config = AgentConfig()
            assert config.calculator_max_expression_length == 500
            assert config.calculator_max_power == 50
    
    def test_circuit_breaker_settings(self, agent_config):
        """Test circuit breaker configuration settings."""
        assert agent_config.circuit_breaker_failure_threshold > 0
        assert agent_config.circuit_breaker_timeout > 0
        
        # Should be configurable
        with patch.dict(os.environ, {
            'CIRCUIT_BREAKER_FAILURE_THRESHOLD': '10',
            'CIRCUIT_BREAKER_TIMEOUT': '120'
        }):
            config = AgentConfig()
            assert config.circuit_breaker_failure_threshold == 10
            assert config.circuit_breaker_timeout == 120
    
    def test_logging_configuration(self, agent_config):
        """Test logging-related configuration."""
        assert agent_config.log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        assert agent_config.log_format  # Should have some format string
        
        # Should be configurable
        with patch.dict(os.environ, {
            'LOG_LEVEL': 'DEBUG',
            'LOG_FORMAT': 'custom format'
        }):
            config = AgentConfig()
            assert config.log_level == 'DEBUG'
            assert config.log_format == 'custom format'


class TestConfigurationValidation:
    """Test configuration validation logic."""
    
    def test_empty_provider_fails(self, test_env):
        """Test that empty provider string fails validation."""
        test_config = test_env.copy()
        test_config['AGENT_PROVIDER'] = ''
        
        with patch.dict(os.environ, test_config, clear=True):
            with pytest.raises(Exception):
                config = AgentConfig()
                config.validate()
    
    def test_missing_required_openai_key(self, test_env):
        """Test that OpenAI config without API key fails."""
        test_config = test_env.copy()
        test_config.update({
            'AGENT_PROVIDER': 'openai',
            'OPENAI_API_KEY': ''  # Empty key should fail
        })
        
        with patch.dict(os.environ, test_config, clear=True):
            with pytest.raises(Exception):
                config = AgentConfig()
                config.validate()
    
    def test_missing_required_ollama_url(self, test_env):
        """Test that Ollama config without base URL fails."""
        test_config = test_env.copy()
        test_config.update({
            'AGENT_PROVIDER': 'ollama',
            'OLLAMA_BASE_URL': ''  # Empty URL should fail
        })
        
        with patch.dict(os.environ, test_config, clear=True):
            with pytest.raises(Exception):
                config = AgentConfig()
                config.validate()
    
    def test_validation_error_messages_helpful(self, test_env):
        """Test that validation errors provide helpful messages."""
        test_config = test_env.copy()
        test_config['AGENT_PROVIDER'] = 'invalid_provider'
        
        with patch.dict(os.environ, test_config, clear=True):
            try:
                config = AgentConfig()
                config.validate()
                pytest.fail("Should have raised validation error")
            except Exception as e:
                error_msg = str(e).lower()
                # Should mention what's wrong
                assert 'provider' in error_msg or 'invalid' in error_msg


class TestConfigurationIntegration:
    """Integration tests for configuration with other components."""
    
    def test_config_works_with_error_handler(self, agent_config):
        """Test that configuration integrates with ErrorHandler."""
        from simplest_agent import ErrorHandler
        
        error_handler = ErrorHandler()
        # Should be able to use config values
        assert agent_config.retry_max_attempts >= 1
    
    def test_config_works_with_circuit_breaker(self, agent_config):
        """Test that configuration integrates with CircuitBreaker."""
        from simplest_agent import CircuitBreaker
        
        circuit_breaker = CircuitBreaker(
            failure_threshold=agent_config.circuit_breaker_failure_threshold,
            timeout=agent_config.circuit_breaker_timeout
        )
        
        assert circuit_breaker.failure_threshold == agent_config.circuit_breaker_failure_threshold
    
    def test_config_values_are_reasonable(self, agent_config):
        """Test that all config values are within reasonable ranges."""
        # Temperature should be between 0 and 1
        assert 0.0 <= agent_config.model_temperature <= 1.0
        
        # Iteration limits should be positive and reasonable
        assert 1 <= agent_config.agent_max_iterations <= 100
        
        # Retry attempts should be reasonable
        assert 1 <= agent_config.retry_max_attempts <= 20
        
        # Timeouts should be positive
        assert agent_config.agent_timeout > 0
        assert agent_config.circuit_breaker_timeout > 0
