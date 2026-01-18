"""Authentication utilities for Supabase JWT verification."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel

from kitchen_mate.config import Settings, get_settings


class User(BaseModel):
    """Authenticated user model."""

    id: str
    email: str | None = None


# Default user for single-tenant mode
DEFAULT_USER = User(id="local", email=None)


def verify_jwt_token(token: str, settings: Settings) -> dict:
    """Verify Supabase JWT token and return claims.

    Args:
        token: JWT access token from Supabase
        settings: Application settings with JWT secret

    Returns:
        Decoded JWT claims dictionary

    Raises:
        HTTPException: If token is invalid or verification fails
    """
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=500, detail="Authentication not configured")

    try:
        # Verify and decode the JWT
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",  # Supabase default audience
        )
        return payload
    except JWTError as error:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from error


def extract_user_from_claims(claims: dict) -> User:
    """Extract user information from JWT claims.

    Args:
        claims: Decoded JWT claims dictionary

    Returns:
        User model with ID and email
    """
    return User(
        id=claims.get("sub", ""),  # "sub" claim is user ID
        email=claims.get("email"),
    )


async def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> User:
    """FastAPI dependency to get the current authenticated user.

    Extracts JWT from cookie, verifies it, and returns user.

    Args:
        access_token: JWT token from httpOnly cookie
        settings: Application settings

    Returns:
        Authenticated user

    Raises:
        HTTPException 401: If token is missing or invalid
    """
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    claims = verify_jwt_token(access_token, settings)
    return extract_user_from_claims(claims)


async def get_current_user_optional(
    access_token: Annotated[str | None, Cookie()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> User | None:
    """FastAPI dependency to optionally get the current user.

    Similar to get_current_user but returns None if not authenticated
    instead of raising an exception.

    Args:
        access_token: JWT token from httpOnly cookie
        settings: Application settings

    Returns:
        Authenticated user or None
    """
    if not access_token:
        return None

    try:
        claims = verify_jwt_token(access_token, settings)
        return extract_user_from_claims(claims)
    except HTTPException:
        return None


async def get_user(
    access_token: Annotated[str | None, Cookie()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> User:
    """FastAPI dependency for user-gated routes.

    Handles both single-tenant and multi-tenant modes:
    - Single-tenant: Returns DEFAULT_USER (no auth required)
    - Multi-tenant: Requires valid JWT, returns authenticated user or 401

    Use this for routes that require a user context (e.g., saving recipes).
    Public routes (e.g., clipping) don't need this dependency.

    Args:
        access_token: JWT token from cookie (only used in multi-tenant mode)
        settings: Application settings

    Returns:
        User object (default user in single-tenant, authenticated user in multi-tenant)

    Raises:
        HTTPException 401: If multi-tenant and not authenticated
    """
    if settings.is_single_tenant:
        return DEFAULT_USER

    # Multi-tenant mode: require authentication
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    claims = verify_jwt_token(access_token, settings)
    return extract_user_from_claims(claims)
