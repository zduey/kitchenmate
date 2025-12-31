"""LLM-based recipe parser using Claude API."""

from anthropic import Anthropic
from pydantic import HttpUrl

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
    # TODO: Condense into a single API call
    if model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model: {model}. Supported models: {', '.join(sorted(SUPPORTED_MODELS))}"
        )

    client = Anthropic(api_key=api_key)

    website_to_text_prompt = f"""Extract only the recipe from the following url and output as plain text with recipe title, ingredient list, instructions, and metadata (prep time, cook time, total time, categories). Match the original wording as closely as possible: {url}"""

    try:
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": website_to_text_prompt}],
            tools=[
                {
                    "type": "web_fetch_20250910",
                    "name": "web_fetch",
                    "max_uses": 1,
                }
            ],
            extra_headers={"anthropic-beta": "web-fetch-2025-09-10"},
        )
    except Exception as error:
        raise LLMError(f"Claude API call failed for {url}: {error}") from error

    recipe_text = message.content[2].text

    recipe_parsing_prompt = f"""Parse the following text-based recipe into a structured output with the following elements:
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
    
    Recipe:

    {recipe_text}
"""
    try:
        message = client.beta.messages.parse(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": recipe_parsing_prompt}],
            output_format=Recipe,
            betas=["structured-outputs-2025-11-13"],
        )
    except Exception as error:
        raise LLMError(f"Claude API call failed for {url}: {error}") from error

    recipe = message.parsed_output

    return recipe.model_copy(update={"source_url": HttpUrl(url)})
