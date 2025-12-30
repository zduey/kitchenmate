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
    if model not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unsupported model: {model}. Supported models: {', '.join(sorted(SUPPORTED_MODELS))}"
        )

    client = Anthropic(api_key=api_key)

    prompt = f"""Please visit this URL and extract the recipe:

{url}

Extract:
- Recipe title
- All ingredients with amounts, units, and preparation methods when available
- Step-by-step instructions
- Metadata: author, servings, prep time, cook time, total time, categories
- Image URL if present

Focus on the main recipe content and ignore ads, navigation, and other page elements."""

    try:
        message = client.beta.messages.parse(
            model=model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            output_format=Recipe,
            betas=["structured-outputs-2025-11-13"],
        )
    except Exception as error:
        raise LLMError(f"Claude API call failed for {url}: {error}") from error

    recipe = message.parsed_output

    return recipe.model_copy(update={'source_url': HttpUrl(url)})
