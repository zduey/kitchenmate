"""Tests for LLM-based recipe parser."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pytest

# Check if anthropic is installed
try:
    import anthropic  # noqa: F401

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Skip entire module if anthropic is not installed
pytestmark = pytest.mark.skipif(
    not ANTHROPIC_AVAILABLE,
    reason="anthropic library not installed (install with: pip install recipe-clipper[llm])",
)

# ruff: noqa: E402
from recipe_clipper.parsers.llm_parser import (
    parse_with_claude,
    parse_recipe_from_image,
    parse_recipe_from_document,
    SUPPORTED_MODELS,
)
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

    mock_message = Mock()
    mock_message.parsed_output = mock_recipe

    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.beta.messages.parse.return_value = mock_message
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
    mock_client.beta.messages.parse.assert_called_once()
    call_args = mock_client.beta.messages.parse.call_args
    assert call_args.kwargs["model"] == "claude-sonnet-4-5"
    assert call_args.kwargs["output_format"] == Recipe
    assert "structured-outputs-2025-11-13" in call_args.kwargs["betas"]
    assert "web-fetch-2025-09-10" in call_args.kwargs["betas"]


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

    mock_message = Mock()
    mock_message.parsed_output = mock_recipe

    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.beta.messages.parse.return_value = mock_message
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

    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.beta.messages.parse.side_effect = Exception("API rate limit exceeded")
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

    mock_message = Mock()
    mock_message.parsed_output = mock_recipe

    with patch("anthropic.Anthropic") as mock_anthropic_class:
        mock_client = Mock()
        mock_client.beta.messages.parse.return_value = mock_message
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


def test_parse_recipe_from_image_success():
    """Test successful recipe extraction from an image."""
    api_key = "sk-ant-test-key"

    mock_recipe = Recipe(
        title="Grandma's Apple Pie",
        ingredients=[
            Ingredient(name="6 apples", amount="6", unit="whole"),
            Ingredient(name="2 cups flour", amount="2", unit="cups"),
            Ingredient(name="1 cup sugar", amount="1", unit="cup"),
        ],
        instructions=[
            "Peel and slice apples",
            "Mix dry ingredients",
            "Combine and bake at 350F for 45 minutes",
        ],
        source_url="file:///tmp/recipe.jpg",
    )

    mock_message = Mock()
    mock_message.parsed_output = mock_recipe

    # Create a temporary image file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
        tmp_file.write(b"fake image data")
        image_path = tmp_file.name

    try:
        with patch("anthropic.Anthropic") as mock_anthropic_class:
            with patch("builtins.open", mock_open(read_data=b"fake image data")):
                mock_client = Mock()
                mock_client.beta.messages.parse.return_value = mock_message
                mock_anthropic_class.return_value = mock_client

                recipe = parse_recipe_from_image(image_path, api_key)

        assert isinstance(recipe, Recipe)
        assert recipe.title == "Grandma's Apple Pie"
        assert len(recipe.ingredients) == 3
        assert recipe.ingredients[0].name == "6 apples"
        assert len(recipe.instructions) == 3
        assert recipe.source_url.scheme == "file"

        # Verify API call
        mock_anthropic_class.assert_called_once_with(api_key=api_key)
        mock_client.beta.messages.parse.assert_called_once()
        call_args = mock_client.beta.messages.parse.call_args

        # Check that the message contains an image
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "image"
        assert content[0]["source"]["type"] == "base64"
        assert content[0]["source"]["media_type"] == "image/jpeg"
        assert content[1]["type"] == "text"

        # Verify structured outputs
        assert call_args.kwargs["model"] == "claude-sonnet-4-5"
        assert call_args.kwargs["output_format"] == Recipe
        assert "structured-outputs-2025-11-13" in call_args.kwargs["betas"]
    finally:
        # Clean up temporary file
        Path(image_path).unlink()


def test_parse_recipe_from_image_file_not_found():
    """Test error when image file doesn't exist."""
    api_key = "sk-ant-test-key"
    image_path = "/nonexistent/path/to/image.jpg"

    with pytest.raises(FileNotFoundError) as exc_info:
        parse_recipe_from_image(image_path, api_key)

    assert "Image file not found" in str(exc_info.value)
    assert image_path in str(exc_info.value)


def test_parse_recipe_from_image_unsupported_format():
    """Test error when image format is not supported."""
    api_key = "sk-ant-test-key"

    # Create a temporary file with unsupported extension
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as tmp_file:
        tmp_file.write(b"fake image data")
        image_path = tmp_file.name

    try:
        with pytest.raises(ValueError) as exc_info:
            parse_recipe_from_image(image_path, api_key)

        assert "Unsupported image format" in str(exc_info.value)
        assert ".bmp" in str(exc_info.value)
    finally:
        # Clean up temporary file
        Path(image_path).unlink()


def test_parse_recipe_from_image_unsupported_model():
    """Test error when using unsupported model."""
    api_key = "sk-ant-test-key"
    invalid_model = "gpt-4"

    # Create a temporary image file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
        tmp_file.write(b"fake image data")
        image_path = tmp_file.name

    try:
        with pytest.raises(ValueError) as exc_info:
            parse_recipe_from_image(image_path, api_key, model=invalid_model)

        assert "Unsupported model" in str(exc_info.value)
        assert invalid_model in str(exc_info.value)
        assert all(model in str(exc_info.value) for model in SUPPORTED_MODELS)
    finally:
        # Clean up temporary file
        Path(image_path).unlink()


def test_parse_recipe_from_image_api_error():
    """Test handling of API errors."""
    api_key = "sk-ant-test-key"

    # Create a temporary image file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_file.write(b"fake image data")
        image_path = tmp_file.name

    try:
        with patch("anthropic.Anthropic") as mock_anthropic_class:
            with patch("builtins.open", mock_open(read_data=b"fake image data")):
                mock_client = Mock()
                mock_client.beta.messages.parse.side_effect = Exception("API rate limit exceeded")
                mock_anthropic_class.return_value = mock_client

                with pytest.raises(LLMError) as exc_info:
                    parse_recipe_from_image(image_path, api_key)

                assert "Claude API call failed for image" in str(exc_info.value)
                assert image_path in str(exc_info.value)
                assert "API rate limit exceeded" in str(exc_info.value)
    finally:
        # Clean up temporary file
        Path(image_path).unlink()


def test_parse_recipe_from_image_different_formats():
    """Test that different image formats are handled correctly."""
    api_key = "sk-ant-test-key"

    formats = [
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".png", "image/png"),
        (".gif", "image/gif"),
        (".webp", "image/webp"),
    ]

    mock_recipe = Recipe(
        title="Test Recipe",
        ingredients=[Ingredient(name="ingredient")],
        instructions=["step 1"],
        source_url="file:///tmp/test.jpg",
    )

    mock_message = Mock()
    mock_message.parsed_output = mock_recipe

    for extension, expected_media_type in formats:
        # Create a temporary file with the extension
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            image_path = tmp_file.name

        try:
            with patch("anthropic.Anthropic") as mock_anthropic_class:
                with patch("builtins.open", mock_open(read_data=b"fake image data")):
                    mock_client = Mock()
                    mock_client.beta.messages.parse.return_value = mock_message
                    mock_anthropic_class.return_value = mock_client

                    parse_recipe_from_image(image_path, api_key)

                    # Verify the correct media type was used
                    call_args = mock_client.beta.messages.parse.call_args
                    messages = call_args.kwargs["messages"]
                    media_type = messages[0]["content"][0]["source"]["media_type"]
                    assert media_type == expected_media_type, (
                        f"Failed for {extension}: expected {expected_media_type}, got {media_type}"
                    )
        finally:
            # Clean up temporary file
            Path(image_path).unlink()


def test_parse_recipe_from_document_pdf_success():
    """Test successful recipe extraction from a PDF document."""
    api_key = "sk-ant-test-key"

    mock_recipe = Recipe(
        title="Chocolate Cake",
        ingredients=[
            Ingredient(name="2 cups flour", amount="2", unit="cups"),
            Ingredient(name="1.5 cups sugar", amount="1.5", unit="cups"),
            Ingredient(name="3/4 cup cocoa powder", amount="3/4", unit="cup"),
        ],
        instructions=[
            "Preheat oven to 350F",
            "Mix dry ingredients in a bowl",
            "Add wet ingredients and mix until smooth",
            "Pour into greased pan",
            "Bake for 30-35 minutes",
        ],
        source_url="file:///tmp/recipe.pdf",
        metadata=RecipeMetadata(
            author="Betty Crocker",
            servings="12 servings",
            prep_time=15,
            cook_time=35,
            total_time=50,
        ),
    )

    mock_message = Mock()
    mock_message.parsed_output = mock_recipe

    # Create a temporary PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(b"fake pdf data")
        doc_path = tmp_file.name

    try:
        with patch("anthropic.Anthropic") as mock_anthropic_class:
            with patch("builtins.open", mock_open(read_data=b"fake pdf data")):
                mock_client = Mock()
                mock_client.beta.messages.parse.return_value = mock_message
                mock_anthropic_class.return_value = mock_client

                recipe = parse_recipe_from_document(doc_path, api_key)

        assert isinstance(recipe, Recipe)
        assert recipe.title == "Chocolate Cake"
        assert len(recipe.ingredients) == 3
        assert len(recipe.instructions) == 5
        assert recipe.source_url.scheme == "file"

        # Verify API call
        mock_anthropic_class.assert_called_once_with(api_key=api_key)
        mock_client.beta.messages.parse.assert_called_once()
        call_args = mock_client.beta.messages.parse.call_args

        # Check that the message contains a document
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        content = messages[0]["content"]
        assert len(content) == 2
        assert content[0]["type"] == "document"
        assert content[0]["source"]["type"] == "base64"
        assert content[0]["source"]["media_type"] == "application/pdf"
        assert content[1]["type"] == "text"

        # Verify structured outputs and PDF beta
        assert call_args.kwargs["model"] == "claude-sonnet-4-5"
        assert call_args.kwargs["output_format"] == Recipe
        assert "structured-outputs-2025-11-13" in call_args.kwargs["betas"]
        assert "pdfs-2024-09-25" in call_args.kwargs["betas"]
    finally:
        # Clean up temporary file
        Path(doc_path).unlink()


def test_parse_recipe_from_document_txt_success():
    """Test successful recipe extraction from a text file."""
    api_key = "sk-ant-test-key"

    mock_recipe = Recipe(
        title="Simple Pasta",
        ingredients=[
            Ingredient(name="1 lb pasta"),
            Ingredient(name="2 cups tomato sauce"),
        ],
        instructions=["Boil pasta", "Heat sauce", "Combine and serve"],
        source_url="file:///tmp/recipe.txt",
    )

    mock_message = Mock()
    mock_message.parsed_output = mock_recipe

    # Create a temporary text file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
        tmp_file.write(b"fake text data")
        doc_path = tmp_file.name

    try:
        with patch("anthropic.Anthropic") as mock_anthropic_class:
            with patch("builtins.open", mock_open(read_data=b"fake text data")):
                mock_client = Mock()
                mock_client.beta.messages.parse.return_value = mock_message
                mock_anthropic_class.return_value = mock_client

                recipe = parse_recipe_from_document(doc_path, api_key)

        assert isinstance(recipe, Recipe)
        assert recipe.title == "Simple Pasta"

        # Verify API call
        call_args = mock_client.beta.messages.parse.call_args
        messages = call_args.kwargs["messages"]
        content = messages[0]["content"]
        assert content[0]["source"]["media_type"] == "text/plain"
        # Text files should not include PDF beta
        assert "pdfs-2024-09-25" not in call_args.kwargs["betas"]
    finally:
        # Clean up temporary file
        Path(doc_path).unlink()


def test_parse_recipe_from_document_markdown_success():
    """Test successful recipe extraction from a markdown file."""
    api_key = "sk-ant-test-key"

    mock_recipe = Recipe(
        title="Markdown Recipe",
        ingredients=[Ingredient(name="ingredient")],
        instructions=["step 1"],
        source_url="file:///tmp/recipe.md",
    )

    mock_message = Mock()
    mock_message.parsed_output = mock_recipe

    # Create a temporary markdown file
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp_file:
        tmp_file.write(b"# Recipe\n\nIngredients:\n- ingredient\n\nInstructions:\n1. step 1")
        doc_path = tmp_file.name

    try:
        with patch("anthropic.Anthropic") as mock_anthropic_class:
            with patch("builtins.open", mock_open(read_data=b"fake markdown data")):
                mock_client = Mock()
                mock_client.beta.messages.parse.return_value = mock_message
                mock_anthropic_class.return_value = mock_client

                parse_recipe_from_document(doc_path, api_key)

        # Verify markdown media type
        call_args = mock_client.beta.messages.parse.call_args
        messages = call_args.kwargs["messages"]
        content = messages[0]["content"]
        assert content[0]["source"]["media_type"] == "text/markdown"
    finally:
        # Clean up temporary file
        Path(doc_path).unlink()


def test_parse_recipe_from_document_docx_success():
    """Test successful recipe extraction from a Word document."""
    api_key = "sk-ant-test-key"

    mock_recipe = Recipe(
        title="Word Recipe",
        ingredients=[Ingredient(name="ingredient")],
        instructions=["step 1"],
        source_url="file:///tmp/recipe.docx",
    )

    mock_message = Mock()
    mock_message.parsed_output = mock_recipe

    # Create a temporary docx file
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_file:
        tmp_file.write(b"fake docx data")
        doc_path = tmp_file.name

    try:
        with patch("anthropic.Anthropic") as mock_anthropic_class:
            with patch("builtins.open", mock_open(read_data=b"fake docx data")):
                mock_client = Mock()
                mock_client.beta.messages.parse.return_value = mock_message
                mock_anthropic_class.return_value = mock_client

                parse_recipe_from_document(doc_path, api_key)

        # Verify docx media type
        call_args = mock_client.beta.messages.parse.call_args
        messages = call_args.kwargs["messages"]
        content = messages[0]["content"]
        assert (
            content[0]["source"]["media_type"]
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    finally:
        # Clean up temporary file
        Path(doc_path).unlink()


def test_parse_recipe_from_document_file_not_found():
    """Test error when document file doesn't exist."""
    api_key = "sk-ant-test-key"
    doc_path = "/nonexistent/path/to/document.pdf"

    with pytest.raises(FileNotFoundError) as exc_info:
        parse_recipe_from_document(doc_path, api_key)

    assert "Document file not found" in str(exc_info.value)
    assert doc_path in str(exc_info.value)


def test_parse_recipe_from_document_unsupported_format():
    """Test error when document format is not supported."""
    api_key = "sk-ant-test-key"

    # Create a temporary file with unsupported extension
    with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp_file:
        tmp_file.write(b"fake document data")
        doc_path = tmp_file.name

    try:
        with pytest.raises(ValueError) as exc_info:
            parse_recipe_from_document(doc_path, api_key)

        assert "Unsupported document format" in str(exc_info.value)
        assert ".doc" in str(exc_info.value)
        assert ".pdf" in str(exc_info.value)
        assert ".txt" in str(exc_info.value)
    finally:
        # Clean up temporary file
        Path(doc_path).unlink()


def test_parse_recipe_from_document_unsupported_model():
    """Test error when using unsupported model."""
    api_key = "sk-ant-test-key"
    invalid_model = "gpt-4"

    # Create a temporary PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(b"fake pdf data")
        doc_path = tmp_file.name

    try:
        with pytest.raises(ValueError) as exc_info:
            parse_recipe_from_document(doc_path, api_key, model=invalid_model)

        assert "Unsupported model" in str(exc_info.value)
        assert invalid_model in str(exc_info.value)
        assert all(model in str(exc_info.value) for model in SUPPORTED_MODELS)
    finally:
        # Clean up temporary file
        Path(doc_path).unlink()


def test_parse_recipe_from_document_api_error():
    """Test handling of API errors."""
    api_key = "sk-ant-test-key"

    # Create a temporary PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(b"fake pdf data")
        doc_path = tmp_file.name

    try:
        with patch("anthropic.Anthropic") as mock_anthropic_class:
            with patch("builtins.open", mock_open(read_data=b"fake pdf data")):
                mock_client = Mock()
                mock_client.beta.messages.parse.side_effect = Exception("API rate limit exceeded")
                mock_anthropic_class.return_value = mock_client

                with pytest.raises(LLMError) as exc_info:
                    parse_recipe_from_document(doc_path, api_key)

                assert "Claude API call failed for document" in str(exc_info.value)
                assert doc_path in str(exc_info.value)
                assert "API rate limit exceeded" in str(exc_info.value)
    finally:
        # Clean up temporary file
        Path(doc_path).unlink()
