"""
LangSmith Observability Module

This module provides LangSmith tracing and observability utilities for the
module-2-2 research agent backend.

Exports:
    - langsmith_config: LangSmith configuration singleton
    - get_user_metadata: Generate user-scoped metadata for traces
    - get_user_tags: Generate user-scoped tags for traces
"""

from .config import langsmith_config
from .tracing import get_user_metadata, get_user_tags

__all__ = ["langsmith_config", "get_user_metadata", "get_user_tags"]
