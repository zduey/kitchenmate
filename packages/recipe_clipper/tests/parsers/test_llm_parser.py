"""Tests for LLM-based recipe parser."""

import os
from unittest.mock import Mock, patch
import pytest

from recipe_clipper.parsers.llm_parser import parse_with_claude, SUPPORTED_MODELS
from recipe_clipper.models import Recipe, Ingredient, RecipeMetadata
from recipe_clipper.exceptions import LLMError


def test_parse_with_claude_success():
    """Test successful recipe extraction with Claude."""
    url = "https://example.com/recipe"
    api_key = "sk-ant-test-key"

    mock_recipe = Recipe(
        title="Chocolate Chip Cookies",
        ingredients=[
            Ingredient(name="2 cups flour", amount="2", unit="cups"),
            Ingredient(name="1 cup sugar", amount="1", unit="cups"),
        ],
        instructions=[
            "Preheat oven to 350F",
            "Mix ingredients",
            "Bake for 12 minutes",
        ],
        source_url="https://example.com/different-url",
        image="https://example.com/image.jpg",
        metadata=RecipeMetadata(
            author="Test Chef",
            servings="24 cookies",
            prep_time=15,
            cook_time=12,
            total_time=27,
            categories=["Dessert"],
        ),
    )

    # Mock first API call (text extraction)
    mock_text_message = Mock()
    mock_text_content = Mock()
    mock_text_content.text = "Recipe text content"
    mock_text_message.content = [None, None, mock_text_content]

    # Mock second API call (structured parsing)
    mock_parse_message = Mock()
    mock_parse_message.parsed_output = mock_recipe

    with patch("recipe_clipper.parsers.llm_parser.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_text_message
        mock_client.beta.messages.parse.return_value = mock_parse_message
        mock_anthropic_class.return_value = mock_client

        recipe = parse_with_claude(url, api_key)

    assert isinstance(recipe, Recipe)
    assert recipe.title == "Chocolate Chip Cookies"
    assert len(recipe.ingredients) == 2
    assert recipe.ingredients[0].name == "2 cups flour"
    assert len(recipe.instructions) == 3
    assert str(recipe.source_url) == url
    assert str(recipe.image) == "https://example.com/image.jpg"
    assert recipe.metadata.author == "Test Chef"

    mock_anthropic_class.assert_called_once_with(api_key=api_key)
    mock_client.messages.create.assert_called_once()
    mock_client.beta.messages.parse.assert_called_once()
    call_args = mock_client.beta.messages.parse.call_args
    assert call_args.kwargs["model"] == "claude-sonnet-4-5"
    assert call_args.kwargs["output_format"] == Recipe
    assert "structured-outputs-2025-11-13" in call_args.kwargs["betas"]


def test_parse_with_claude_custom_model():
    """Test using a custom supported model."""
    url = "https://example.com/recipe"
    api_key = "sk-ant-test-key"
    model = "claude-opus-4"

    mock_recipe = Recipe(
        title="Simple Recipe",
        ingredients=[Ingredient(name="1 cup water")],
        instructions=["Boil water"],
        source_url="https://example.com/recipe",
    )

    # Mock first API call
    mock_text_message = Mock()
    mock_text_content = Mock()
    mock_text_content.text = "Recipe text"
    mock_text_message.content = [None, None, mock_text_content]

    # Mock second API call
    mock_parse_message = Mock()
    mock_parse_message.parsed_output = mock_recipe

    with patch("recipe_clipper.parsers.llm_parser.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_text_message
        mock_client.beta.messages.parse.return_value = mock_parse_message
        mock_anthropic_class.return_value = mock_client

        recipe = parse_with_claude(url, api_key, model=model)

    assert recipe.title == "Simple Recipe"

    call_args = mock_client.beta.messages.parse.call_args
    assert call_args.kwargs["model"] == model


def test_parse_with_claude_unsupported_model():
    """Test error when using unsupported model."""
    url = "https://example.com/recipe"
    api_key = "sk-ant-test-key"
    invalid_model = "gpt-4"

    with pytest.raises(ValueError) as exc_info:
        parse_with_claude(url, api_key, model=invalid_model)

    assert "Unsupported model" in str(exc_info.value)
    assert invalid_model in str(exc_info.value)
    assert all(model in str(exc_info.value) for model in SUPPORTED_MODELS)


def test_parse_with_claude_api_error():
    """Test handling of API errors."""
    url = "https://example.com/recipe"
    api_key = "sk-ant-test-key"

    with patch("recipe_clipper.parsers.llm_parser.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API rate limit exceeded")
        mock_anthropic_class.return_value = mock_client

        with pytest.raises(LLMError) as exc_info:
            parse_with_claude(url, api_key)

        assert "Claude API call failed" in str(exc_info.value)
        assert url in str(exc_info.value)
        assert "API rate limit exceeded" in str(exc_info.value)


def test_parse_with_claude_source_url_override():
    """Test that source_url is set to the URL parameter, not the extracted value."""
    url = "https://example.com/recipe"
    api_key = "sk-ant-test-key"

    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[Ingredient(name="ingredient")],
        instructions=["step 1"],
        source_url="https://different.com/url",
    )

    # Mock first API call
    mock_text_message = Mock()
    mock_text_content = Mock()
    mock_text_content.text = "Recipe text"
    mock_text_message.content = [None, None, mock_text_content]

    # Mock second API call
    mock_parse_message = Mock()
    mock_parse_message.parsed_output = mock_recipe

    with patch("recipe_clipper.parsers.llm_parser.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_text_message
        mock_client.beta.messages.parse.return_value = mock_parse_message
        mock_anthropic_class.return_value = mock_client

        recipe = parse_with_claude(url, api_key)

    assert str(recipe.source_url) == url
    assert str(recipe.source_url) != "https://different.com/url"


@pytest.mark.integration
def test_parse_with_claude_integration():
    """Integration test that makes a real API call to Claude.

    Uses a recipe from Smitten Kitchen, which is not supported by recipe-scrapers.
    Requires ANTHROPIC_API_KEY environment variable to be set.
    Run with: pytest -m integration
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY environment variable not set")

    url = "http://smittenkitchen.com/2011/02/meatball-sub-with-caramelized-onions/"

    recipe = parse_with_claude(url, api_key)

    assert isinstance(recipe, Recipe)
    assert recipe.title
    assert len(recipe.ingredients) > 0
    assert len(recipe.instructions) > 0
    assert str(recipe.source_url) == url
    assert recipe.metadata is not None
