"""Pytest fixtures for KitchenMate API tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from kitchen_mate.config import Settings, get_settings
from kitchen_mate.main import app

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app with caching disabled.

    Default client runs in single-tenant mode (pro tier by default).
    """
    # Disable caching and Supabase auth for tests by default
    # (explicit None overrides .env file values)
    test_settings = Settings(cache_enabled=False, supabase_jwt_secret=None, supabase_url=None)
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def settings_with_api_key(client: TestClient) -> Generator[None, None, None]:
    """Override settings to include an API key (single-tenant, pro tier)."""
    test_settings = Settings(
        anthropic_api_key="test-api-key", cache_enabled=False, supabase_url=None
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def settings_without_api_key(client: TestClient) -> Generator[None, None, None]:
    """Override settings to have no API key."""
    test_settings = Settings(anthropic_api_key=None, cache_enabled=False, supabase_url=None)
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def settings_free_tier(client: TestClient) -> Generator[None, None, None]:
    """Override settings for multi-tenant mode with no pro users (free tier)."""
    test_settings = Settings(
        anthropic_api_key="test-api-key",
        supabase_jwt_secret="test-secret-key-at-least-32-characters-long",
        pro_user_ids=set(),
        cache_enabled=False,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def settings_pro_tier(client: TestClient) -> Generator[None, None, None]:
    """Override settings for multi-tenant mode with test user as pro."""
    test_settings = Settings(
        anthropic_api_key="test-api-key",
        supabase_jwt_secret="test-secret-key-at-least-32-characters-long",
        pro_user_ids={"test-user-123"},
        cache_enabled=False,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def settings_with_supabase(client: TestClient) -> Generator[Settings, None, None]:
    """Override settings with Supabase configuration for HS256 JWT verification."""
    test_settings = Settings(
        supabase_jwt_secret="test-secret-key-at-least-32-characters-long",
        supabase_url=None,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield test_settings
    app.dependency_overrides.clear()
