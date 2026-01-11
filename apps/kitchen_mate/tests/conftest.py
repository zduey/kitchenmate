"""Pytest fixtures for KitchenMate API tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from kitchen_mate.config import Settings
from kitchen_mate.main import app

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def settings_with_api_key() -> Generator[None, None, None]:
    """Override settings to include an API key."""
    test_settings = Settings(anthropic_api_key="test-api-key")
    with patch("kitchen_mate.routes.clip.get_settings", return_value=test_settings):
        yield


@pytest.fixture
def settings_without_api_key() -> Generator[None, None, None]:
    """Override settings to have no API key."""
    test_settings = Settings(anthropic_api_key=None)
    with patch("kitchen_mate.routes.clip.get_settings", return_value=test_settings):
        yield
