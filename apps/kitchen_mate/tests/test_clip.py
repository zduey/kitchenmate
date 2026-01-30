"""Tests for the /api/clip endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from recipe_clipper.exceptions import NetworkError, RecipeParsingError
from recipe_clipper.models import Recipe

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_clip_recipe_returns_json(client: TestClient) -> None:
    """Test clipping a recipe returns JSON."""
    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[],
        instructions=["Step 1", "Step 2"],
        source_url="https://example.com/recipe",
    )
    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    with patch("kitchen_mate.extraction.fetch_url", return_value=mock_response):
        with patch("kitchen_mate.extraction.parse_with_recipe_scrapers", return_value=mock_recipe):
            response = client.post(
                "/api/clip",
                json={"url": "https://example.com/recipe", "use_llm_fallback": False},
            )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["recipe"]["title"] == "Test Recipe"
    assert data["recipe"]["instructions"] == ["Step 1", "Step 2"]
    assert data["cached"] is False


def test_clip_recipe_not_found(client: TestClient) -> None:
    """Test handling of recipe not found error."""
    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    with patch("kitchen_mate.extraction.fetch_url", return_value=mock_response):
        with patch(
            "kitchen_mate.extraction.parse_with_recipe_scrapers",
            side_effect=RecipeParsingError("Recipe not found"),
        ):
            response = client.post(
                "/api/clip",
                json={"url": "https://example.com/recipe", "use_llm_fallback": False},
            )

    assert response.status_code == 500
    assert "Failed to parse recipe" in response.json()["detail"]


def test_clip_recipe_network_error(client: TestClient) -> None:
    """Test handling of network error."""
    with patch(
        "kitchen_mate.extraction.fetch_url",
        side_effect=NetworkError("Connection failed"),
    ):
        response = client.post(
            "/api/clip",
            json={"url": "https://example.com/recipe", "use_llm_fallback": False},
        )

    assert response.status_code == 502
    assert "Failed to fetch URL" in response.json()["detail"]


def test_clip_recipe_llm_fallback_without_api_key(
    client: TestClient, settings_without_api_key: None
) -> None:
    """Test that LLM fallback fails without API key when parsing fails."""
    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    with patch("kitchen_mate.extraction.fetch_url", return_value=mock_response):
        with patch(
            "kitchen_mate.extraction.parse_with_recipe_scrapers",
            side_effect=RecipeParsingError("Not supported"),
        ):
            response = client.post(
                "/api/clip",
                json={"url": "https://example.com/recipe", "use_llm_fallback": True},
            )

    assert response.status_code == 500
    assert "Failed to parse" in response.json()["detail"]


def test_clip_recipe_invalid_url(client: TestClient) -> None:
    """Test validation of invalid URL."""
    response = client.post(
        "/api/clip",
        json={"url": "not-a-valid-url", "use_llm_fallback": False},
    )

    assert response.status_code == 422


def test_clip_recipe_timeout_bounds(client: TestClient) -> None:
    """Test validation of timeout bounds."""
    response = client.post(
        "/api/clip",
        json={"url": "https://example.com/recipe", "timeout": 100, "use_llm_fallback": False},
    )

    assert response.status_code == 422


def test_clip_recipe_llm_fallback_free_tier_blocked(
    client: TestClient, settings_free_tier: None
) -> None:
    """Test that LLM fallback is blocked for free tier users when recipe_scrapers fails."""
    from tests.test_auth import create_test_jwt

    token = create_test_jwt(
        "free-user-456",
        "free@example.com",
        "test-secret-key-at-least-32-characters-long",
    )

    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    with patch("kitchen_mate.extraction.fetch_url", return_value=mock_response):
        with patch(
            "kitchen_mate.extraction.parse_with_recipe_scrapers",
            side_effect=RecipeParsingError("Not supported"),
        ):
            response = client.post(
                "/api/clip",
                json={"url": "https://example.com/recipe", "use_llm_fallback": True},
                cookies={"access_token": token},
            )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error_code"] == "upgrade_required"
    assert detail["feature"] == "clip_ai"


def test_clip_recipe_llm_fallback_pro_tier_allowed(
    client: TestClient, settings_pro_tier: None
) -> None:
    """Test that LLM fallback works for pro tier users."""
    from tests.test_auth import create_test_jwt

    token = create_test_jwt(
        "test-user-123",
        "pro@example.com",
        "test-secret-key-at-least-32-characters-long",
    )

    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    with patch("kitchen_mate.extraction.fetch_url", return_value=mock_response):
        with patch(
            "kitchen_mate.extraction.parse_with_recipe_scrapers",
            side_effect=RecipeParsingError("Not supported"),
        ):
            with patch("recipe_clipper.parsers.llm_parser.parse_with_claude") as mock_llm:
                mock_llm.return_value = Recipe(
                    title="LLM Recipe",
                    ingredients=[],
                    instructions=["Step 1"],
                    source_url="https://example.com/recipe",
                )
                response = client.post(
                    "/api/clip",
                    json={"url": "https://example.com/recipe", "use_llm_fallback": True},
                    cookies={"access_token": token},
                )

    assert response.status_code == 200
    assert response.json()["recipe"]["title"] == "LLM Recipe"
    assert response.json()["cached"] is False


def test_clip_recipe_single_tenant_allows_llm(
    client: TestClient, settings_with_api_key: None
) -> None:
    """Test that LLM fallback works in single-tenant mode (all users are pro)."""
    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    with patch("kitchen_mate.extraction.fetch_url", return_value=mock_response):
        with patch(
            "kitchen_mate.extraction.parse_with_recipe_scrapers",
            side_effect=RecipeParsingError("Not supported"),
        ):
            with patch("recipe_clipper.parsers.llm_parser.parse_with_claude") as mock_llm:
                mock_llm.return_value = Recipe(
                    title="LLM Recipe",
                    ingredients=[],
                    instructions=["Step 1"],
                    source_url="https://example.com/recipe",
                )
                response = client.post(
                    "/api/clip",
                    json={"url": "https://example.com/recipe", "use_llm_fallback": True},
                )

    assert response.status_code == 200
    assert response.json()["recipe"]["title"] == "LLM Recipe"
    assert response.json()["cached"] is False


def test_clip_recipe_no_llm_fallback_works_for_free_tier(
    client: TestClient, settings_free_tier: None
) -> None:
    """Test that basic clipping (no LLM) works for free tier users."""
    from tests.test_auth import create_test_jwt

    token = create_test_jwt(
        "free-user-456",
        "free@example.com",
        "test-secret-key-at-least-32-characters-long",
    )

    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[],
        instructions=["Step 1"],
        source_url="https://example.com/recipe",
    )
    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    with patch("kitchen_mate.extraction.fetch_url", return_value=mock_response):
        with patch("kitchen_mate.extraction.parse_with_recipe_scrapers", return_value=mock_recipe):
            response = client.post(
                "/api/clip",
                json={"url": "https://example.com/recipe", "use_llm_fallback": False},
                cookies={"access_token": token},
            )

    assert response.status_code == 200
    assert response.json()["recipe"]["title"] == "Test Recipe"
    assert response.json()["cached"] is False


def test_clip_recipe_unauthenticated_basic_clipping_works(
    client: TestClient, settings_free_tier: None
) -> None:
    """Test that unauthenticated users can use basic clipping in multi-tenant mode."""
    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[],
        instructions=["Step 1"],
        source_url="https://example.com/recipe",
    )
    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    # No auth token - unauthenticated request
    with patch("kitchen_mate.extraction.fetch_url", return_value=mock_response):
        with patch("kitchen_mate.extraction.parse_with_recipe_scrapers", return_value=mock_recipe):
            response = client.post(
                "/api/clip",
                json={"url": "https://example.com/recipe"},
            )

    assert response.status_code == 200
    assert response.json()["recipe"]["title"] == "Test Recipe"


def test_clip_recipe_unauthenticated_llm_fallback_blocked(
    client: TestClient, settings_free_tier: None
) -> None:
    """Test that unauthenticated users cannot use LLM fallback in multi-tenant mode."""
    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    # No auth token - unauthenticated request
    with patch("kitchen_mate.extraction.fetch_url", return_value=mock_response):
        with patch(
            "kitchen_mate.extraction.parse_with_recipe_scrapers",
            side_effect=RecipeParsingError("Not supported"),
        ):
            response = client.post(
                "/api/clip",
                json={"url": "https://example.com/recipe", "use_llm_fallback": True},
            )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error_code"] == "upgrade_required"
    assert detail["feature"] == "clip_ai"


def test_clip_recipe_unauthenticated_force_llm_blocked(
    client: TestClient, settings_free_tier: None
) -> None:
    """Test that unauthenticated users cannot force LLM in multi-tenant mode."""
    # No auth token - unauthenticated request
    response = client.post(
        "/api/clip",
        json={"url": "https://example.com/recipe", "force_llm": True},
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error_code"] == "upgrade_required"
    assert detail["feature"] == "clip_ai"
