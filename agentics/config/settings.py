"""
Configuration management system for the agentics package.

This module provides comprehensive configuration management with environment
variable integration and validation.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentConfig:
    """Comprehensive configuration management for the agent."""

    # Model Configuration
    model_name: str = field(default_factory=lambda: os.getenv("AGENT_MODEL", "llama3.2:3b"))
    model_provider: str = field(default_factory=lambda: os.getenv("AGENT_PROVIDER", "ollama"))
    model_temperature: float = field(default_factory=lambda: float(os.getenv("AGENT_TEMPERATURE", "0.0")))

    # API Configuration
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_api_base: str = field(default_factory=lambda: os.getenv("OPENAI_API_BASE", ""))
    litellm_key: str = field(default_factory=lambda: os.getenv("LITELLM_KEY", ""))
    litellm_base_url: str = field(default_factory=lambda: os.getenv("LITELLM_BASE_URL", "http://127.0.0.1:4000"))

    # Agent Behavior Configuration
    agent_verbose: bool = field(default_factory=lambda: os.getenv("AGENT_VERBOSE", "true").lower() == "true")
    agent_max_iterations: int = field(default_factory=lambda: int(os.getenv("AGENT_MAX_ITERATIONS", "15")))
    agent_timeout: int = field(default_factory=lambda: int(os.getenv("AGENT_TIMEOUT", "300")))

    # Retry Configuration
    retry_max_attempts: int = field(default_factory=lambda: int(os.getenv("RETRY_MAX_ATTEMPTS", "3")))
    retry_base_delay: float = field(default_factory=lambda: float(os.getenv("RETRY_BASE_DELAY", "1.0")))
    retry_max_delay: float = field(default_factory=lambda: float(os.getenv("RETRY_MAX_DELAY", "60.0")))

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = field(default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")))
    circuit_breaker_timeout: int = field(default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60")))

    # Calculator Configuration
    calculator_max_expression_length: int = field(default_factory=lambda: int(os.getenv("CALCULATOR_MAX_LENGTH", "1000")))
    calculator_max_power: int = field(default_factory=lambda: int(os.getenv("CALCULATOR_MAX_POWER", "100")))

    # Logging Configuration
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_format: str = field(default_factory=lambda: os.getenv("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s"))

    # Memory Configuration
    memory_key: str = field(default_factory=lambda: os.getenv("MEMORY_KEY", "chat_history"))
    memory_return_messages: bool = field(default_factory=lambda: os.getenv("MEMORY_RETURN_MESSAGES", "true").lower() == "true")

    def validate(self) -> List[str]:
        """Validate configuration and return list of validation errors."""
        errors = []

        # Validate model configuration
        if not self.model_name:
            errors.append("AGENT_MODEL cannot be empty")

        if self.model_provider not in ["ollama", "openai", "litellm"]:
            errors.append(f"AGENT_PROVIDER must be one of: ollama, openai, litellm. Got: {self.model_provider}")

        if not (0.0 <= self.model_temperature <= 2.0):
            errors.append(f"AGENT_TEMPERATURE must be between 0.0 and 2.0. Got: {self.model_temperature}")

        # Validate API configuration based on provider
        if self.model_provider == "ollama" and not self.ollama_base_url:
            errors.append("OLLAMA_BASE_URL is required when using ollama provider")

        if self.model_provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required when using openai provider")

        if self.model_provider == "litellm" and not self.litellm_key:
            errors.append("LITELLM_KEY is required when using litellm provider")

        # Validate numeric ranges
        if self.agent_max_iterations < 1:
            errors.append(f"AGENT_MAX_ITERATIONS must be >= 1. Got: {self.agent_max_iterations}")

        if self.agent_timeout < 1:
            errors.append(f"AGENT_TIMEOUT must be >= 1. Got: {self.agent_timeout}")

        if self.retry_max_attempts < 1:
            errors.append(f"RETRY_MAX_ATTEMPTS must be >= 1. Got: {self.retry_max_attempts}")

        if self.retry_base_delay <= 0:
            errors.append(f"RETRY_BASE_DELAY must be > 0. Got: {self.retry_base_delay}")

        if self.retry_max_delay <= self.retry_base_delay:
            errors.append(f"RETRY_MAX_DELAY must be > RETRY_BASE_DELAY. Got: {self.retry_max_delay} <= {self.retry_base_delay}")

        if self.circuit_breaker_failure_threshold < 1:
            errors.append(f"CIRCUIT_BREAKER_FAILURE_THRESHOLD must be >= 1. Got: {self.circuit_breaker_failure_threshold}")

        if self.circuit_breaker_timeout < 1:
            errors.append(f"CIRCUIT_BREAKER_TIMEOUT must be >= 1. Got: {self.circuit_breaker_timeout}")

        if self.calculator_max_expression_length < 10:
            errors.append(f"CALCULATOR_MAX_LENGTH must be >= 10. Got: {self.calculator_max_expression_length}")

        if self.calculator_max_power < 1:
            errors.append(f"CALCULATOR_MAX_POWER must be >= 1. Got: {self.calculator_max_power}")

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of: {valid_log_levels}. Got: {self.log_level}")

        return errors

    def setup_environment(self) -> None:
        """Set up environment variables for compatibility with existing code."""
        # Set up OpenAI environment variables for LangChain compatibility
        if self.model_provider == "openai":
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
            if self.openai_api_base:
                os.environ["OPENAI_API_BASE"] = self.openai_api_base
        elif self.model_provider == "litellm":
            os.environ["OPENAI_API_KEY"] = self.litellm_key
            os.environ["OPENAI_API_BASE"] = self.litellm_base_url

        # Set up logging configuration
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format
        )

    def get_model_kwargs(self) -> Dict[str, Any]:
        """Get model initialization parameters based on provider."""
        base_kwargs = {
            "model": self.model_name,
            "temperature": self.model_temperature
        }

        if self.model_provider == "ollama":
            base_kwargs.update({
                "provider": "ollama",
                "base_url": self.ollama_base_url
            })

        return base_kwargs

    def __post_init__(self):
        """Validate configuration after initialization."""
        validation_errors = self.validate()
        if validation_errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in validation_errors)
            
            # Import here to avoid circular dependency
            from ..error_handling import AgentError, ErrorCategory
            
            raise AgentError(
                error_message,
                ErrorCategory.CONFIGURATION,
                context={"validation_errors": validation_errors},
                user_message="The agent configuration has invalid settings. Please check your environment variables.",
                recovery_suggestions=[
                    "Review and correct the environment variables mentioned in the errors",
                    "Check the documentation for valid configuration values",
                    "Ensure all required environment variables are set for your chosen provider"
                ]
            )

        # Set up environment after successful validation
        self.setup_environment()
