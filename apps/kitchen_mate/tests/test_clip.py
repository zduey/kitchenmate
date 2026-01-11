"""Tests for the /clip endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from recipe_clipper.exceptions import NetworkError, RecipeNotFoundError
from recipe_clipper.models import Recipe

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_clip_recipe_json_format(client: TestClient) -> None:
    """Test clipping a recipe with JSON format."""
    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[],
        instructions=["Step 1", "Step 2"],
        source_url="https://example.com/recipe",
    )

    with patch("kitchen_mate.routes.clip.clip_recipe", return_value=mock_recipe):
        response = client.post(
            "/clip",
            json={"url": "https://example.com/recipe", "format": "json"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["title"] == "Test Recipe"
    assert data["instructions"] == ["Step 1", "Step 2"]


def test_clip_recipe_text_format(client: TestClient) -> None:
    """Test clipping a recipe with text format."""
    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[],
        instructions=["Step 1"],
    )

    with patch("kitchen_mate.routes.clip.clip_recipe", return_value=mock_recipe):
        response = client.post(
            "/clip",
            json={"url": "https://example.com/recipe", "format": "text"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "Test Recipe" in response.text


def test_clip_recipe_markdown_format(client: TestClient) -> None:
    """Test clipping a recipe with markdown format."""
    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[],
        instructions=["Step 1"],
    )

    with patch("kitchen_mate.routes.clip.clip_recipe", return_value=mock_recipe):
        response = client.post(
            "/clip",
            json={"url": "https://example.com/recipe", "format": "markdown"},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "# Test Recipe" in response.text


def test_clip_recipe_download(client: TestClient) -> None:
    """Test clipping a recipe with download flag."""
    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[],
        instructions=["Step 1"],
    )

    with patch("kitchen_mate.routes.clip.clip_recipe", return_value=mock_recipe):
        response = client.post(
            "/clip",
            json={
                "url": "https://example.com/recipe",
                "format": "json",
                "download": True,
            },
        )

    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert 'filename="recipe.json"' in response.headers.get("content-disposition", "")


def test_clip_recipe_not_found(client: TestClient) -> None:
    """Test handling of recipe not found error."""
    with patch(
        "kitchen_mate.routes.clip.clip_recipe",
        side_effect=RecipeNotFoundError("Recipe not found"),
    ):
        response = client.post(
            "/clip",
            json={"url": "https://example.com/recipe"},
        )

    assert response.status_code == 404
    assert "Recipe not found" in response.json()["detail"]


def test_clip_recipe_network_error(client: TestClient) -> None:
    """Test handling of network error."""
    with patch(
        "kitchen_mate.routes.clip.clip_recipe",
        side_effect=NetworkError("Connection failed"),
    ):
        response = client.post(
            "/clip",
            json={"url": "https://example.com/recipe"},
        )

    assert response.status_code == 502
    assert "Failed to fetch URL" in response.json()["detail"]


def test_clip_recipe_llm_fallback_without_api_key(
    client: TestClient, settings_without_api_key: None
) -> None:
    """Test that LLM fallback fails without API key."""
    response = client.post(
        "/clip",
        json={"url": "https://example.com/recipe", "use_llm_fallback": True},
    )

    assert response.status_code == 400
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_clip_recipe_invalid_url(client: TestClient) -> None:
    """Test validation of invalid URL."""
    response = client.post(
        "/clip",
        json={"url": "not-a-valid-url"},
    )

    assert response.status_code == 422


def test_clip_recipe_timeout_bounds(client: TestClient) -> None:
    """Test validation of timeout bounds."""
    response = client.post(
        "/clip",
        json={"url": "https://example.com/recipe", "timeout": 100},
    )

    assert response.status_code == 422
