"""LLM-based recipe parser using Claude API."""

import base64
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from pydantic import AnyUrl

from recipe_clipper.models import Recipe
from recipe_clipper.exceptions import LLMError

if TYPE_CHECKING:
    from anthropic import Anthropic


SUPPORTED_MODELS = {
    "claude-sonnet-4-5",
    "claude-sonnet-4",
    "claude-opus-4",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
}

IMAGE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

DOCUMENT_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# Helper functions for common LLM parsing operations


def _validate_model(model: str) -> None:
    """Validate that the model is supported."""
    if model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model: {model}. Supported models: {', '.join(sorted(SUPPORTED_MODELS))}"
        )


def _validate_file_path(file_path: Path, file_description: str) -> None:
    """Validate that a file exists."""
    if not file_path.exists():
        raise FileNotFoundError(f"{file_description} not found: {file_path}")


def _read_and_encode_file(file_path: Path) -> str:
    """Read a file and return base64-encoded data."""
    with open(file_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _get_recipe_extraction_prompt(source_type: str = "document") -> str:
    """Get the standard recipe extraction prompt.

    Args:
        source_type: Type of source ("image", "document", or "webpage")

    Returns:
        Formatted prompt string
    """
    if source_type == "image":
        visibility_note = (
            "If any information is not visible in the image, omit it from the output.\n"
            "Extract the text exactly as it appears, preserving the original wording and formatting."
        )
    else:
        visibility_note = (
            "If any information is not present in the document, omit it from the output.\n"
            "Extract the text exactly as it appears, preserving the original wording."
        )

    return f"""Extract the recipe from this {source_type} into a structured output with the following elements:
    - title
    - ingredients
        - amount
        - units
        - preparation method, if available
        - original wording as the display_text
    - instructions
    - metadata
        - author (if visible)
        - number of servings (if visible)
        - prep time (if visible)
        - cook time (if visible)
        - total time (if visible)
        - categories (if visible)

    {visibility_note}
    """


def _call_claude_api(
    client: "Anthropic",
    model: str,
    messages: list,
    betas: list[str],
    source_description: str,
    tools: Optional[list] = None,
) -> Recipe:
    """Make a Claude API call with error handling.

    Args:
        client: Anthropic client instance
        model: Model name to use
        messages: Messages to send
        betas: Beta features to enable
        source_description: Description of source for error messages
        tools: Optional tools to provide

    Returns:
        Parsed Recipe object

    Raises:
        LLMError: If API call fails
    """
    try:
        kwargs = {
            "model": model,
            "max_tokens": 4096,
            "messages": messages,
            "output_format": Recipe,
            "betas": betas,
        }
        if tools:
            kwargs["tools"] = tools

        message = client.beta.messages.parse(**kwargs)
        return message.parsed_output
    except Exception as error:
        raise LLMError(f"Claude API call failed for {source_description}: {error}") from error


def _set_recipe_source_url(recipe: Recipe, source_path: Union[str, Path]) -> Recipe:
    """Set the source URL for a recipe.

    Args:
        recipe: Recipe object to update
        source_path: Source path (URL string or file path)

    Returns:
        Updated Recipe object with source_url set
    """
    if isinstance(source_path, str) and source_path.startswith("http"):
        source_url = AnyUrl(source_path)
    else:
        source_url = AnyUrl(Path(source_path).absolute().as_uri())
    return recipe.model_copy(update={"source_url": source_url})


def _validate_file_format(
    file_path: Path, media_type_map: dict[str, str], format_category: str
) -> str:
    """Validate file format and return media type.

    Args:
        file_path: Path to the file
        media_type_map: Mapping of file extensions to media types
        format_category: Category description for error message

    Returns:
        Media type string

    Raises:
        ValueError: If file format is not supported
    """
    extension = file_path.suffix.lower()

    if extension not in media_type_map:
        raise ValueError(
            f"Unsupported {format_category} format: {extension}. "
            f"Supported formats: {', '.join(media_type_map.keys())}"
        )

    return media_type_map[extension]


def parse_with_claude(url: str, api_key: str, model: str = "claude-sonnet-4-5") -> Recipe:
    """Parse a recipe using Claude's structured output API.

    Args:
        url: URL of the recipe page
        api_key: Anthropic API key
        model: Claude model to use (default: claude-sonnet-4-5)

    Returns:
        Parsed Recipe object

    Raises:
        ValueError: If an unsupported model is specified
        LLMError: If Claude API call fails
    """
    from anthropic import Anthropic

    _validate_model(model)

    client = Anthropic(api_key=api_key)

    prompt = f"{_get_recipe_extraction_prompt('webpage')}\n\nURL:\n\n{url}"
    messages = [{"role": "user", "content": prompt}]

    tools = [
        {
            "type": "web_fetch_20250910",
            "name": "web_fetch",
            "max_uses": 1,
        }
    ]

    recipe = _call_claude_api(
        client=client,
        model=model,
        messages=messages,
        betas=["structured-outputs-2025-11-13", "web-fetch-2025-09-10"],
        source_description=url,
        tools=tools,
    )

    return _set_recipe_source_url(recipe, url)


def parse_recipe_from_image(
    image_path: Union[str, Path], api_key: str, model: str = "claude-sonnet-4-5"
) -> Recipe:
    """Parse a recipe from an image using Claude's vision API.

    Useful for extracting recipes from cookbook photos, handwritten recipe cards,
    or screenshots of recipes.

    Args:
        image_path: Path to the image file (jpg, png, gif, webp)
        api_key: Anthropic API key
        model: Claude model to use (default: claude-sonnet-4-5)

    Returns:
        Parsed Recipe object

    Raises:
        ValueError: If an unsupported model is specified or image format is invalid
        FileNotFoundError: If the image file doesn't exist
        LLMError: If Claude API call fails
    """
    from anthropic import Anthropic

    _validate_model(model)

    image_file = Path(image_path)
    _validate_file_path(image_file, "Image file")

    media_type = _validate_file_format(image_file, IMAGE_MEDIA_TYPES, "image")
    image_data = _read_and_encode_file(image_file)

    client = Anthropic(api_key=api_key)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": _get_recipe_extraction_prompt("image")},
            ],
        }
    ]

    recipe = _call_claude_api(
        client=client,
        model=model,
        messages=messages,
        betas=["structured-outputs-2025-11-13"],
        source_description=f"image {image_path}",
    )

    return _set_recipe_source_url(recipe, image_file)


def parse_recipe_from_document(
    document_path: Union[str, Path], api_key: str, model: str = "claude-sonnet-4-5"
) -> Recipe:
    """Parse a recipe from a document using Claude's file API.

    Supports PDF, Word documents (.docx), and text formats (.txt, .md).
    Uses Claude's native document handling capabilities.

    Args:
        document_path: Path to the document file (pdf, docx, txt, md)
        api_key: Anthropic API key
        model: Claude model to use (default: claude-sonnet-4-5)

    Returns:
        Parsed Recipe object

    Raises:
        ValueError: If an unsupported model or document format is specified
        FileNotFoundError: If the document file doesn't exist
        LLMError: If Claude API call fails
    """
    from anthropic import Anthropic

    _validate_model(model)

    doc_file = Path(document_path)
    _validate_file_path(doc_file, "Document file")

    media_type = _validate_file_format(doc_file, DOCUMENT_MEDIA_TYPES, "document")
    document_data = _read_and_encode_file(doc_file)

    client = Anthropic(api_key=api_key)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": document_data,
                    },
                },
                {"type": "text", "text": _get_recipe_extraction_prompt("document")},
            ],
        }
    ]

    # Add PDF beta if needed
    betas = ["structured-outputs-2025-11-13"]
    if doc_file.suffix.lower() == ".pdf":
        betas.append("pdfs-2024-09-25")

    recipe = _call_claude_api(
        client=client,
        model=model,
        messages=messages,
        betas=betas,
        source_description=f"document {document_path}",
    )

    return _set_recipe_source_url(recipe, doc_file)
