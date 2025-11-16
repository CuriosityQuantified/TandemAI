"""
Date utility functions for consistent date handling across all prompts.

This module provides standardized date formatting for system prompts to ensure
all agents have access to the current date in a consistent format.
"""

from datetime import datetime


def get_current_date() -> str:
    """
    Get the current date in YYYY-MM-DD format.

    This format is used consistently across all system prompts to provide
    agents with temporal context for their responses.

    Returns:
        str: Current date in YYYY-MM-DD format (e.g., "2025-01-10")

    Examples:
        >>> from utils.date_helper import get_current_date
        >>> current_date = get_current_date()
        >>> print(f"Today's date: {current_date}")
        Today's date: 2025-01-10
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_current_datetime() -> str:
    """
    Get the current date and time in YYYY-MM-DD HH:MM:SS format.

    Returns:
        str: Current datetime in YYYY-MM-DD HH:MM:SS format

    Examples:
        >>> from utils.date_helper import get_current_datetime
        >>> current_datetime = get_current_datetime()
        >>> print(f"Current datetime: {current_datetime}")
        Current datetime: 2025-01-10 14:30:45
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
