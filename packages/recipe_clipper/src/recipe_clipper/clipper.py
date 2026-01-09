"""Main clipper orchestration for extracting recipes from URLs."""

from typing import Optional

from recipe_clipper.models import Recipe
from recipe_clipper.http import fetch_url
from recipe_clipper.parsers.recipe_scrapers_parser import parse_with_recipe_scrapers
from recipe_clipper.exceptions import RecipeParsingError


def clip_recipe(
    url: str,
    api_key: Optional[str] = None,
    use_llm_fallback: bool = True,
    timeout: int = 10,
) -> Recipe:
    """
    Extract a recipe from a URL.

    Tries recipe-scrapers library first. If that fails and LLM fallback is enabled,
    falls back to Claude-based extraction.

    Args:
        url: The URL of the recipe page to extract
        api_key: Anthropic API key for LLM fallback
        use_llm_fallback: Whether to use LLM fallback if recipe-scrapers fails (default: True)
        timeout: HTTP request timeout in seconds (default: 10)

    Returns:
        Parsed Recipe object

    Raises:
        ValueError: If use_llm_fallback is True but api_key is not provided
        RecipeNotFoundError: If the recipe cannot be extracted
        NetworkError: If the HTTP request fails
        RecipeParsingError: If parsing fails unexpectedly
        LLMError: If LLM API call fails
    """
    if use_llm_fallback and not api_key:
        raise ValueError("api_key must be provided when use_llm_fallback is True")

    try:
        response = fetch_url(url, timeout=timeout)
        return parse_with_recipe_scrapers(response)
    except RecipeParsingError:
        if use_llm_fallback:
            from recipe_clipper.parsers.llm_parser import parse_with_claude

            return parse_with_claude(url, api_key)
        raise
