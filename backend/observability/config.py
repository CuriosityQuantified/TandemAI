"""
LangSmith Configuration Module

Provides centralized configuration for LangSmith observability.
Uses pydantic BaseSettings for environment variable management.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class LangSmithConfig(BaseSettings):
    """
    LangSmith configuration settings loaded from environment variables.

    Attributes:
        enabled: Whether LangSmith tracing is enabled
        api_key: LangSmith API key for authentication
        endpoint: LangSmith API endpoint URL
        project: Project name for organizing traces
    """

    enabled: bool = Field(
        default=False,
        description="Enable/disable LangSmith tracing"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="LangSmith API key"
    )
    endpoint: str = Field(
        default="https://api.smith.langchain.com",
        description="LangSmith API endpoint"
    )
    project: str = Field(
        default="module-2-2-research-agent",
        description="LangSmith project name"
    )

    class Config:
        """Pydantic configuration."""
        case_sensitive = False

    def __init__(self, **kwargs):
        """Initialize config with environment variable support."""
        # Manual loading for explicit environment variable mapping
        super().__init__(
            enabled=os.getenv("LANGSMITH_TRACING", "false").lower() == "true",
            api_key=os.getenv("LANGSMITH_API_KEY"),
            endpoint=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
            project=os.getenv("LANGSMITH_PROJECT", "module-2-2-research-agent"),
            **kwargs
        )


# Singleton instance
langsmith_config = LangSmithConfig()
