"""Tests for recipe formatters."""

import json
import pytest
from recipe_clipper.formatters import (
    format_recipe_text,
    format_recipe_json,
    format_recipe_markdown,
)
from recipe_clipper.models import Recipe, Ingredient, RecipeMetadata


@pytest.fixture
def sample_recipe():
    """Sample recipe for testing formatters."""
    return Recipe(
        title="Chocolate Chip Cookies",
        ingredients=[
            Ingredient(name="2 cups flour"),
            Ingredient(name="1 cup sugar"),
            Ingredient(name="2 cups chocolate chips"),
        ],
        instructions=[
            "Preheat oven to 350F",
            "Mix dry ingredients",
            "Add chocolate chips",
            "Bake for 12 minutes",
        ],
        source_url="https://example.com/recipe",
        image="https://example.com/image.jpg",
        metadata=RecipeMetadata(
            author="Test Chef",
            servings="24 cookies",
            prep_time=15,
            cook_time=12,
            total_time=27,
            categories=["Dessert", "Cookies"],
        ),
    )


def test_format_recipe_text(sample_recipe):
    """Test text formatter output."""
    output = format_recipe_text(sample_recipe)

    expected = "\n================================================================================\n                             Chocolate Chip Cookies                             \n================================================================================\n\nMETADATA\n--------------------------------------------------------------------------------\nAuthor: Test Chef\nServings: 24 cookies\nPrep Time: 15 minutes\nCook Time: 12 minutes\nTotal Time: 27 minutes\nCategories: Dessert, Cookies\n\nINGREDIENTS\n--------------------------------------------------------------------------------\n  • 2 cups flour\n  • 1 cup sugar\n  • 2 cups chocolate chips\n\nINSTRUCTIONS\n--------------------------------------------------------------------------------\n1. Preheat oven to 350F\n2. Mix dry ingredients\n3. Add chocolate chips\n4. Bake for 12 minutes\n\nSource: https://example.com/recipe\n"

    assert output == expected


def test_format_recipe_json(sample_recipe):
    """Test JSON formatter output."""
    output = format_recipe_json(sample_recipe)

    # Verify it's valid JSON
    data = json.loads(output)

    # Verify structure
    assert data["title"] == "Chocolate Chip Cookies"
    assert len(data["ingredients"]) == 3
    assert data["ingredients"][0]["name"] == "2 cups flour"
    assert len(data["instructions"]) == 4
    assert data["instructions"][0] == "Preheat oven to 350F"
    assert data["source_url"] == "https://example.com/recipe"
    assert data["metadata"]["author"] == "Test Chef"
    assert data["metadata"]["servings"] == "24 cookies"


def test_format_recipe_markdown(sample_recipe):
    """Test Markdown formatter output."""
    output = format_recipe_markdown(sample_recipe)

    expected = "# Chocolate Chip Cookies\n\n## Metadata\n\n- **Author:** Test Chef\n- **Servings:** 24 cookies\n- **Prep Time:** 15 minutes\n- **Cook Time:** 12 minutes\n- **Total Time:** 27 minutes\n- **Categories:** Dessert, Cookies\n\n## Ingredients\n\n- 2 cups flour\n- 1 cup sugar\n- 2 cups chocolate chips\n\n## Instructions\n\n1. Preheat oven to 350F\n2. Mix dry ingredients\n3. Add chocolate chips\n4. Bake for 12 minutes\n\n## Source\n\n[https://example.com/recipe](https://example.com/recipe)\n"

    assert output == expected
