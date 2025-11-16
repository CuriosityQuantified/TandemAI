"""
Utility functions for the backend application.

This package provides shared utility functions used across different modules,
including date formatting, validation helpers, and other common utilities.
"""

from backend.utils.date_helper import get_current_date, get_current_datetime

__all__ = ["get_current_date", "get_current_datetime"]
