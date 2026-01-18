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
    """Create a test client for the FastAPI app with caching disabled."""
    # Disable caching and Supabase auth for tests by default
    # (explicit None overrides .env file values)
    test_settings = Settings(cache_enabled=False, supabase_jwt_secret=None)
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def settings_with_api_key(client: TestClient) -> Generator[None, None, None]:
    """Override settings to include an API key."""
    test_settings = Settings(anthropic_api_key="test-api-key", cache_enabled=False)
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def settings_without_api_key(client: TestClient) -> Generator[None, None, None]:
    """Override settings to have no API key."""
    test_settings = Settings(anthropic_api_key=None, cache_enabled=False)
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def settings_with_api_key_and_ip_whitelist(client: TestClient) -> Generator[None, None, None]:
    """Override settings to include API key and IP whitelist."""
    test_settings = Settings(
        anthropic_api_key="test-api-key",
        llm_allowed_ips="127.0.0.1,192.168.1.0/24",
        cache_enabled=False,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def settings_with_api_key_no_whitelist(client: TestClient) -> Generator[None, None, None]:
    """Override settings to include API key but no IP whitelist (all blocked)."""
    test_settings = Settings(
        anthropic_api_key="test-api-key",
        llm_allowed_ips=None,
        cache_enabled=False,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def settings_with_api_key_allow_all(client: TestClient) -> Generator[None, None, None]:
    """Override settings to include API key with wildcard IP whitelist."""
    test_settings = Settings(
        anthropic_api_key="test-api-key",
        llm_allowed_ips="0.0.0.0/0",
        cache_enabled=False,
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def settings_with_supabase(client: TestClient) -> Generator[Settings, None, None]:
    """Override settings with Supabase configuration."""
    test_settings = Settings(
        supabase_jwt_secret="test-secret-key-at-least-32-characters-long",
    )
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield test_settings
    app.dependency_overrides.clear()
