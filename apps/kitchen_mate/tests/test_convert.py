"""Tests for the /convert endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_convert_recipe_to_text(client: TestClient) -> None:
    """Test converting a recipe to text format."""
    recipe = {
        "title": "Test Recipe",
        "ingredients": [{"name": "flour", "display_text": "2 cups flour"}],
        "instructions": ["Mix ingredients", "Bake at 350F"],
    }

    response = client.post(
        "/convert",
        json={"recipe": recipe, "format": "text"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "Test Recipe" in response.text
    assert "2 cups flour" in response.text
    assert "Mix ingredients" in response.text


def test_convert_recipe_to_markdown(client: TestClient) -> None:
    """Test converting a recipe to markdown format."""
    recipe = {
        "title": "Test Recipe",
        "ingredients": [{"name": "flour", "display_text": "2 cups flour"}],
        "instructions": ["Mix ingredients", "Bake at 350F"],
    }

    response = client.post(
        "/convert",
        json={"recipe": recipe, "format": "markdown"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "attachment" in response.headers.get("content-disposition", "")
    assert "# Test Recipe" in response.text
    assert "- 2 cups flour" in response.text
    assert "1. Mix ingredients" in response.text


def test_convert_recipe_json_format_rejected(client: TestClient) -> None:
    """Test that JSON format is rejected for convert endpoint."""
    recipe = {
        "title": "Test Recipe",
        "ingredients": [],
        "instructions": [],
    }

    response = client.post(
        "/convert",
        json={"recipe": recipe, "format": "json"},
    )

    assert response.status_code == 400
    assert "JSON format not supported" in response.json()["detail"]


def test_convert_recipe_with_metadata(client: TestClient) -> None:
    """Test converting a recipe with metadata."""
    recipe = {
        "title": "Test Recipe",
        "ingredients": [],
        "instructions": ["Step 1"],
        "metadata": {
            "author": "Test Author",
            "servings": "4 servings",
            "prep_time": 15,
            "cook_time": 30,
        },
    }

    response = client.post(
        "/convert",
        json={"recipe": recipe, "format": "text"},
    )

    assert response.status_code == 200
    assert "Test Author" in response.text
    assert "4 servings" in response.text


def test_convert_recipe_missing_required_fields(client: TestClient) -> None:
    """Test validation of missing required fields."""
    response = client.post(
        "/convert",
        json={"recipe": {}, "format": "text"},
    )

    assert response.status_code == 422
