"""
Authentication module for JWT token generation and verification.

This module provides JWT-based authentication for the WebSocket collaborative
editing system. All constants and types follow the Integration Contract.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt


# JWT Configuration (from Integration Contract)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def create_access_token(user_id: str) -> str:
    """
    Generate JWT access token for authenticated user.

    Args:
        user_id: Unique user identifier (UUID string)

    Returns:
        JWT token string (valid for ACCESS_TOKEN_EXPIRE_HOURS)

    Example:
        >>> token = create_access_token("user-123")
        >>> print(token)
        'eyJ0eXAiOiJKV1QiLCJhbGc...'
    """
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }

    encoded_jwt = jwt.encode(
        to_encode,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """
    Verify JWT token and extract user_id.

    Args:
        token: JWT token string

    Returns:
        user_id if valid, None if invalid or expired

    Example:
        >>> user_id = verify_token("eyJ0eXAi...")
        >>> print(user_id)
        'user-123'
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")

        if user_id is None:
            return None

        return user_id

    except JWTError:
        # Invalid token, expired token, or any other JWT error
        return None
    except Exception:
        # Catch any other unexpected errors
        return None
