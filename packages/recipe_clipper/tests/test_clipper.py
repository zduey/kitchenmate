"""Tests for clipper orchestration."""

import os
from unittest.mock import Mock, patch
import pytest

from recipe_clipper.clipper import clip_recipe
from recipe_clipper.models import Recipe, Ingredient
from recipe_clipper.exceptions import RecipeNotFoundError, NetworkError, RecipeParsingError


@pytest.mark.integration
def test_clip_recipe_integration():
    """Integration test using a real recipe URL with network call."""
    # Use a real recipe from AllRecipes (a well-supported site)
    url = "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/"

    # Make real network call and parse (without LLM fallback)
    recipe = clip_recipe(url, use_llm_fallback=False, timeout=30)

    # Verify we got a valid recipe
    assert isinstance(recipe, Recipe)
    assert recipe.title is not None
    assert len(recipe.title) > 0

    # Verify we got ingredients
    assert len(recipe.ingredients) > 0
    assert all(ing.name for ing in recipe.ingredients)

    # Verify we got instructions
    assert len(recipe.instructions) > 0
    assert all(len(step) > 0 for step in recipe.instructions)

    # Verify source URL matches
    assert str(recipe.source_url) == url

    # Verify we have metadata
    assert recipe.metadata is not None

    # Image should be present for AllRecipes
    assert recipe.image is not None


@pytest.mark.integration
def test_clip_recipe_unsupported_site():
    """Test that unsupported sites raise RecipeNotFoundError."""
    # Use a URL from a site that recipe-scrapers doesn't support
    url = "http://smittenkitchen.com/2011/02/meatball-sub-with-caramelized-onions/"

    with pytest.raises(RecipeNotFoundError) as exc_info:
        clip_recipe(url, use_llm_fallback=False, timeout=10)

    assert "does not support" in str(exc_info.value)


@pytest.mark.integration
def test_clip_recipe_invalid_url():
    """Test that invalid URLs raise NetworkError."""
    url = "https://this-domain-does-not-exist-12345.com/recipe"

    with pytest.raises(NetworkError):
        clip_recipe(url, use_llm_fallback=False, timeout=5)


def test_clip_recipe_llm_fallback_requires_api_key():
    """Test that use_llm_fallback=True requires api_key."""
    url = "https://example.com/recipe"

    with pytest.raises(ValueError) as exc_info:
        clip_recipe(url, api_key=None, use_llm_fallback=True)

    assert "api_key must be provided" in str(exc_info.value)


@pytest.mark.integration
def test_clip_recipe_no_llm_fallback_without_api_key():
    """Test that use_llm_fallback=False works without api_key."""
    url = "http://smittenkitchen.com/2011/02/meatball-sub-with-caramelized-onions/"

    with pytest.raises(RecipeNotFoundError):
        clip_recipe(url, api_key=None, use_llm_fallback=False, timeout=10)


def test_clip_recipe_llm_fallback_unit():
    """Unit test for LLM fallback logic with mocked parsers."""
    url = "https://example.com/recipe"
    api_key = "sk-ant-test-key"

    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[Ingredient(name="1 cup water")],
        instructions=["Step 1"],
        source_url=url,
    )

    with patch("recipe_clipper.clipper.fetch_url") as mock_fetch:
        with patch("recipe_clipper.clipper.parse_with_recipe_scrapers") as mock_recipe_scrapers:
            with patch("recipe_clipper.parsers.llm_parser.parse_with_claude") as mock_claude:
                mock_fetch.return_value = Mock(
                    content="<html>test</html>", status_code=200, url=url
                )
                mock_recipe_scrapers.side_effect = RecipeParsingError("Site not supported")
                mock_claude.return_value = mock_recipe

                recipe = clip_recipe(url, api_key=api_key, use_llm_fallback=True)

                assert recipe.title == "Test Recipe"
                mock_recipe_scrapers.assert_called_once()
                mock_claude.assert_called_once_with(url, api_key)


@pytest.mark.integration
def test_clip_recipe_llm_fallback_integration():
    """Integration test for LLM fallback with real API call.

    Uses a recipe from Smitten Kitchen, which is not supported by recipe-scrapers,
    so it will fall back to Claude API.
    Requires ANTHROPIC_API_KEY environment variable to be set.
    Run with: pytest -m integration
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY environment variable not set")

    url = "http://smittenkitchen.com/2011/02/meatball-sub-with-caramelized-onions/"

    recipe = clip_recipe(url, api_key=api_key, use_llm_fallback=True, timeout=30)

    assert isinstance(recipe, Recipe)
    assert recipe.title
    assert len(recipe.ingredients) > 0
    assert len(recipe.instructions) > 0
    assert str(recipe.source_url) == url
