"""
LangSmith Tracing Utilities

Provides helper functions for enriching LangSmith traces with user metadata and tags.
"""

import os
from typing import Optional


def get_user_metadata(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> dict:
    """
    Generate metadata for user-scoped tracing.

    Metadata appears in the LangSmith trace details and can be used for:
    - Filtering traces by user or session
    - Debugging user-specific issues
    - Analytics and usage tracking

    Args:
        user_id: Unique user identifier from JWT token
        session_id: Unique session identifier for this conversation

    Returns:
        Dictionary of metadata key-value pairs

    Example:
        >>> metadata = get_user_metadata("user-123", "session-456")
        >>> print(metadata)
        {
            "environment": "development",
            "version": "2.5",
            "user_id": "user-123",
            "session_id": "session-456",
            "thread_id": "session-456"
        }
    """
    metadata = {
        "environment": os.getenv("DEPLOYMENT_MODE", "development"),
        "version": "2.5",
    }

    if user_id:
        metadata["user_id"] = user_id

    if session_id:
        metadata["session_id"] = session_id
        metadata["thread_id"] = session_id

    return metadata


def get_user_tags(user_id: Optional[str] = None) -> list[str]:
    """
    Generate tags for user-scoped tracing.

    Tags enable fast filtering and grouping in the LangSmith dashboard.
    Use tags for high-level categorization.

    Args:
        user_id: Unique user identifier from JWT token

    Returns:
        List of tag strings

    Example:
        >>> tags = get_user_tags("user-123")
        >>> print(tags)
        ["production", "research-agent", "user:user-123"]
    """
    environment = os.getenv("DEPLOYMENT_MODE", "development")
    tags = [environment, "research-agent"]

    if user_id:
        tags.append(f"user:{user_id}")

    return tags
