"""Authentication utilities for Supabase JWT verification."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated
from urllib.parse import unquote

import httpx
import jwt
from fastapi import Cookie, Depends, HTTPException
from jwt import PyJWKClient
from pydantic import BaseModel

from kitchen_mate.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Cache the JWKS client to avoid fetching keys on every request
_jwks_clients: dict[str, PyJWKClient] = {}


class User(BaseModel):
    """Authenticated user model."""

    id: str
    email: str | None = None


# Default user for single-tenant mode
DEFAULT_USER = User(id="local", email=None)


def get_jwks_client(supabase_url: str) -> PyJWKClient:
    """Get or create a cached JWKS client for the Supabase project."""
    if supabase_url not in _jwks_clients:
        # Supabase GoTrue exposes JWKS at /auth/v1/.well-known/jwks.json
        jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        logger.info("Creating JWKS client for: %s", jwks_url)
        _jwks_clients[supabase_url] = PyJWKClient(jwks_url)
    return _jwks_clients[supabase_url]


def verify_jwt_token(token: str, settings: Settings) -> dict:
    """Verify Supabase JWT token and return claims.

    Supports both:
    - HS256 with JWT secret (legacy)
    - ES256 with JWKS from Supabase URL

    Args:
        token: JWT access token from Supabase
        settings: Application settings

    Returns:
        Decoded JWT claims dictionary

    Raises:
        HTTPException: If token is invalid or verification fails
    """
    if not settings.supabase_jwt_secret and not settings.supabase_url:
        raise HTTPException(status_code=500, detail="Authentication not configured")

    try:
        # Get the token header to determine algorithm
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "unknown")
        logger.info("JWT algorithm: %s", alg)

        if alg == "ES256" and settings.supabase_url:
            # Use JWKS for ES256
            jwks_client = get_jwks_client(settings.supabase_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        elif settings.supabase_jwt_secret:
            # Use JWT secret for HS256
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            logger.warning("No suitable verification method for algorithm: %s", alg)
            raise HTTPException(status_code=500, detail=f"Cannot verify JWT with algorithm {alg}")

        return payload

    except jwt.ExpiredSignatureError as error:
        logger.warning("JWT token expired")
        raise HTTPException(status_code=401, detail="Token expired") from error
    except jwt.InvalidAudienceError as error:
        logger.warning("JWT audience mismatch: %s", error)
        raise HTTPException(status_code=401, detail="Invalid token audience") from error
    except jwt.PyJWTError as error:
        logger.warning("JWT verification failed: %s", error)
        raise HTTPException(status_code=401, detail="Invalid authentication token") from error
    except httpx.HTTPError as error:
        logger.error("Failed to fetch JWKS: %s", error)
        raise HTTPException(status_code=500, detail="Failed to verify token") from error


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

    token = unquote(access_token)
    claims = verify_jwt_token(token, settings)
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
        token = unquote(access_token)
        claims = verify_jwt_token(token, settings)
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
        logger.warning("No access_token cookie received")
        raise HTTPException(status_code=401, detail="Not authenticated")

    # URL-decode the token (in case it was encoded when set)
    token = unquote(access_token)
    logger.info("Received access_token cookie (length: %d)", len(token))
    claims = verify_jwt_token(token, settings)
    return extract_user_from_claims(claims)
