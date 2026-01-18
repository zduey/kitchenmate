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
