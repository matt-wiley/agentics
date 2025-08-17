"""
Configuration package for agentics.

Provides comprehensive configuration management with environment integration.
"""

from .settings import AgentConfig

# Create default global configuration instance
config = AgentConfig()

__all__ = ['AgentConfig', 'config']
