"""Main clipper orchestration for extracting recipes from URLs."""

from recipe_clipper.models import Recipe
from recipe_clipper.http import fetch_url
from recipe_clipper.parsers.recipe_scrapers_parser import parse_with_recipe_scrapers


def clip_recipe(url: str, timeout: int = 10) -> Recipe:
    """
    Extract a recipe from a URL.

    Args:
        url: The URL of the recipe page to extract
        timeout: HTTP request timeout in seconds (default: 10)

    Returns:
        Parsed Recipe object

    Raises:
        RecipeNotFoundError: If the recipe cannot be extracted
        NetworkError: If the HTTP request fails
        RecipeParsingError: If parsing fails unexpectedly
    """
    response = fetch_url(url, timeout=timeout)
    return parse_with_recipe_scrapers(response)
