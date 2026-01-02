"""LLM-based recipe parser using Claude API."""

import base64
from pathlib import Path

from anthropic import Anthropic
from pydantic import AnyUrl

from recipe_clipper.models import Recipe
from recipe_clipper.exceptions import LLMError


SUPPORTED_MODELS = {
    "claude-sonnet-4-5",
    "claude-sonnet-4",
    "claude-opus-4",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
}


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
    if model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model: {model}. Supported models: {', '.join(sorted(SUPPORTED_MODELS))}"
        )

    client = Anthropic(api_key=api_key)

    recipe_from_webpage_prompt = f"""Extract the recipe at the following URL into a structured output with the following elements:
    - title
    - ingredients
        - amount
        - units
        - preparation method, if available
        - original wording as the display_text
    - instructions
    - metadata
        - author
        - number of servings
        - prep time
        - cook time
        - total time
        - categories
    
    URL:

    {url}
    """

    try:
        message = client.beta.messages.parse(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": recipe_from_webpage_prompt}],
            tools=[
                {
                    "type": "web_fetch_20250910",
                    "name": "web_fetch",
                    "max_uses": 1,
                },
            ],
            output_format=Recipe,
            betas=["structured-outputs-2025-11-13", "web-fetch-2025-09-10"],
        )
    except Exception as error:
        raise LLMError(f"Claude API call failed for {url}: {error}") from error

    recipe = message.parsed_output

    return recipe.model_copy(update={"source_url": AnyUrl(url)})


def parse_recipe_from_image(
    image_path: str | Path, api_key: str, model: str = "claude-sonnet-4-5"
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
    if model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model: {model}. Supported models: {', '.join(sorted(SUPPORTED_MODELS))}"
        )

    # Convert to Path object and validate
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Determine media type from extension
    extension = image_file.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }

    if extension not in media_type_map:
        raise ValueError(
            f"Unsupported image format: {extension}. "
            f"Supported formats: {', '.join(media_type_map.keys())}"
        )

    media_type = media_type_map[extension]

    # Read and encode image
    with open(image_file, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    client = Anthropic(api_key=api_key)

    recipe_from_image_prompt = """Extract the recipe from this image into a structured output with the following elements:
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

    If any information is not visible in the image, omit it from the output.
    Extract the text exactly as it appears, preserving the original wording and formatting.
    """

    try:
        message = client.beta.messages.parse(
            model=model,
            max_tokens=4096,
            messages=[
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
                        {"type": "text", "text": recipe_from_image_prompt},
                    ],
                }
            ],
            output_format=Recipe,
            betas=["structured-outputs-2025-11-13"],
        )
    except Exception as error:
        raise LLMError(f"Claude API call failed for image {image_path}: {error}") from error

    recipe = message.parsed_output
    source_url = image_file.absolute().as_uri()
    return recipe.model_copy(update={"source_url": AnyUrl(source_url)})


def parse_recipe_from_document(
    document_path: str | Path, api_key: str, model: str = "claude-sonnet-4-5"
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
    if model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model: {model}. Supported models: {', '.join(sorted(SUPPORTED_MODELS))}"
        )

    # Convert to Path object and validate
    doc_file = Path(document_path)
    if not doc_file.exists():
        raise FileNotFoundError(f"Document file not found: {document_path}")

    # Determine document type and media type from extension
    extension = doc_file.suffix.lower()
    media_type_map = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    if extension not in media_type_map:
        raise ValueError(
            f"Unsupported document format: {extension}. "
            f"Supported formats: {', '.join(media_type_map.keys())}"
        )

    media_type = media_type_map[extension]

    # Read and encode document
    with open(doc_file, "rb") as f:
        document_data = base64.standard_b64encode(f.read()).decode("utf-8")

    client = Anthropic(api_key=api_key)

    recipe_from_document_prompt = """Extract the recipe from this document into a structured output with the following elements:
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

    If any information is not present in the document, omit it from the output.
    Extract the text exactly as it appears, preserving the original wording.
    """

    # Determine which beta features to use based on file type
    betas = ["structured-outputs-2025-11-13"]
    if extension == ".pdf":
        betas.append("pdfs-2024-09-25")

    try:
        message = client.beta.messages.parse(
            model=model,
            max_tokens=4096,
            messages=[
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
                        {"type": "text", "text": recipe_from_document_prompt},
                    ],
                }
            ],
            output_format=Recipe,
            betas=betas,
        )
    except Exception as error:
        raise LLMError(
            f"Claude API call failed for document {document_path}: {error}"
        ) from error

    recipe = message.parsed_output
    source_url = doc_file.absolute().as_uri()
    return recipe.model_copy(update={"source_url": AnyUrl(source_url)})
