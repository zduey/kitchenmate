"""Tests for authentication functionality."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

from kitchen_mate.config import Settings


def create_test_jwt(user_id: str, email: str, secret: str, expired: bool = False) -> str:
    """Create a test JWT token.

    Args:
        user_id: User ID for the token
        email: User email for the token
        secret: JWT secret for signing
        expired: Whether to create an expired token

    Returns:
        Encoded JWT token
    """
    exp = (
        datetime.now(timezone.utc) - timedelta(hours=1)
        if expired
        else datetime.now(timezone.utc) + timedelta(hours=1)
    )

    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "exp": exp,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, secret, algorithm="HS256")


def test_get_current_user_valid_token(client: TestClient, settings_with_supabase: Settings) -> None:
    """Test retrieving current user with valid token."""
    token = create_test_jwt(
        "user-123", "test@example.com", settings_with_supabase.supabase_jwt_secret
    )

    response = client.get("/api/auth/me", cookies={"access_token": token})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "user-123"
    assert data["email"] == "test@example.com"


def test_get_current_user_missing_token(client: TestClient) -> None:
    """Test that missing token returns 401."""
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_get_current_user_invalid_token(
    client: TestClient, settings_with_supabase: Settings
) -> None:
    """Test that invalid token returns 401."""
    response = client.get("/api/auth/me", cookies={"access_token": "invalid-token"})

    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]


def test_get_current_user_expired_token(
    client: TestClient, settings_with_supabase: Settings
) -> None:
    """Test that expired token returns 401."""
    token = create_test_jwt(
        "user-123", "test@example.com", settings_with_supabase.supabase_jwt_secret, expired=True
    )

    response = client.get("/api/auth/me", cookies={"access_token": token})

    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]


def test_get_current_user_no_supabase_config(client: TestClient) -> None:
    """Test that missing Supabase config returns 500."""
    # Use a valid token format but without Supabase configuration
    token = jwt.encode(
        {
            "sub": "user-123",
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "any-secret",
        algorithm="HS256",
    )

    response = client.get("/api/auth/me", cookies={"access_token": token})

    assert response.status_code == 500
    assert "Authentication not configured" in response.json()["detail"]


def test_get_current_user_wrong_audience(
    client: TestClient, settings_with_supabase: Settings
) -> None:
    """Test that token with wrong audience returns 401."""
    # Create token with wrong audience
    payload = {
        "sub": "user-123",
        "email": "test@example.com",
        "aud": "wrong-audience",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    token = jwt.encode(payload, settings_with_supabase.supabase_jwt_secret, algorithm="HS256")

    response = client.get("/api/auth/me", cookies={"access_token": token})

    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]


# Tests for get_user dependency (single-tenant vs multi-tenant)


async def test_get_user_single_tenant_returns_default_user() -> None:
    """Test that get_user returns default user in single-tenant mode."""
    from kitchen_mate.auth import DEFAULT_USER, get_user
    from kitchen_mate.config import Settings

    settings = Settings(supabase_jwt_secret=None)
    assert settings.is_single_tenant

    # In single-tenant mode, get_user should return DEFAULT_USER without any token
    user = await get_user(access_token=None, settings=settings)

    assert user.id == DEFAULT_USER.id
    assert user.email == DEFAULT_USER.email


async def test_get_user_multi_tenant_requires_auth() -> None:
    """Test that get_user requires authentication in multi-tenant mode."""
    import pytest
    from fastapi import HTTPException

    from kitchen_mate.auth import get_user
    from kitchen_mate.config import Settings

    settings = Settings(supabase_jwt_secret="test-secret-key-at-least-32-characters-long")
    assert settings.is_multi_tenant

    # In multi-tenant mode, get_user should raise 401 without token
    with pytest.raises(HTTPException) as exc_info:
        await get_user(access_token=None, settings=settings)

    assert exc_info.value.status_code == 401
    assert "Not authenticated" in exc_info.value.detail


async def test_get_user_multi_tenant_with_valid_token() -> None:
    """Test that get_user returns authenticated user in multi-tenant mode with valid token."""
    from kitchen_mate.auth import get_user
    from kitchen_mate.config import Settings

    secret = "test-secret-key-at-least-32-characters-long"
    settings = Settings(supabase_jwt_secret=secret)

    token = create_test_jwt("user-456", "multi@example.com", secret)

    user = await get_user(access_token=token, settings=settings)

    assert user.id == "user-456"
    assert user.email == "multi@example.com"
