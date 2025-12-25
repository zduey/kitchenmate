"""Tests for clipper orchestration."""

import pytest
from recipe_clipper.clipper import clip_recipe
from recipe_clipper.models import Recipe
from recipe_clipper.exceptions import RecipeNotFoundError, NetworkError


def test_clip_recipe_integration():
    """Integration test using a real recipe URL with network call."""
    # Use a real recipe from AllRecipes (a well-supported site)
    url = "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/"

    # Make real network call and parse
    recipe = clip_recipe(url, timeout=30)

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


def test_clip_recipe_unsupported_site():
    """Test that unsupported sites raise RecipeNotFoundError."""
    # Use a URL from a site that recipe-scrapers doesn't support
    url = "http://smittenkitchen.com/2011/02/meatball-sub-with-caramelized-onions/"

    with pytest.raises(RecipeNotFoundError) as exc_info:
        clip_recipe(url, timeout=10)

    assert "does not support" in str(exc_info.value)


def test_clip_recipe_invalid_url():
    """Test that invalid URLs raise NetworkError."""
    url = "https://this-domain-does-not-exist-12345.com/recipe"

    with pytest.raises(NetworkError):
        clip_recipe(url, timeout=5)
