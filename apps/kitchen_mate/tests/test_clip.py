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


def test_clip_recipe_llm_fallback_ip_not_allowed(
    client: TestClient, settings_with_api_key_and_ip_whitelist: None
) -> None:
    """Test that LLM fallback is blocked when IP is not in whitelist."""
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

    assert response.status_code == 403
    assert "Upgrade" in response.json()["detail"]


def test_clip_recipe_llm_fallback_no_whitelist_blocks_all(
    client: TestClient, settings_with_api_key_no_whitelist: None
) -> None:
    """Test that LLM fallback is blocked when no whitelist is configured."""
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

    assert response.status_code == 403
    assert "Upgrade" in response.json()["detail"]


def test_clip_recipe_llm_fallback_ip_allowed(
    client: TestClient, settings_with_api_key_allow_all: None
) -> None:
    """Test that LLM fallback works when IP is allowed."""
    mock_response = MagicMock()
    mock_response.content = "<html>test</html>"

    with patch("kitchen_mate.extraction.is_ip_allowed", return_value=True):
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


def test_clip_recipe_no_llm_fallback_ignores_whitelist(
    client: TestClient, settings_with_api_key_and_ip_whitelist: None
) -> None:
    """Test that IP whitelist is not checked when LLM fallback is disabled."""
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
            )

    assert response.status_code == 200
    assert response.json()["recipe"]["title"] == "Test Recipe"
    assert response.json()["cached"] is False
