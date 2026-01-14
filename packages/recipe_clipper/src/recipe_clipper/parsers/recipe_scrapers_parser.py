"""Parser using the recipe-scrapers library."""

from typing import Callable, TypeVar

from recipe_scrapers import scrape_html

from recipe_clipper.models import Recipe, Ingredient, RecipeMetadata
from recipe_clipper.http import HttpResponse
from recipe_clipper.exceptions import RecipeParsingError

T = TypeVar("T")


def _safe_get(getter: Callable[[], T]) -> T | None:
    """Safely call a scraper method, returning None if the field is not found."""
    try:
        return getter()
    except Exception:
        return None


def parse_with_recipe_scrapers(response: HttpResponse) -> Recipe:
    """
    Parse a recipe using the recipe-scrapers library.

    Attempts to parse recipes from both supported and unsupported sites using
    generic schema.org markup when site-specific scrapers are unavailable.

    Args:
        response: HttpResponse containing URL and HTML content

    Returns:
        Parsed Recipe object

    Raises:
        RecipeNotFoundError: If no recipe could be found in the page
        RecipeParsingError: If parsing fails
    """
    try:
        scraper = scrape_html(response.content, response.url, supported_only=False)
    except Exception as error:
        raise RecipeParsingError(f"Failed to create scraper for {response.url}: {error}") from error

    ingredients = [Ingredient(name=ingredient) for ingredient in scraper.ingredients()]

    category = _safe_get(scraper.category)
    metadata = RecipeMetadata(
        author=_safe_get(scraper.author),
        servings=_safe_get(scraper.yields),
        prep_time=_safe_get(scraper.prep_time),
        cook_time=_safe_get(scraper.cook_time),
        total_time=_safe_get(scraper.total_time),
        categories=[category] if category else None,
    )

    return Recipe(
        title=scraper.title(),
        ingredients=ingredients,
        instructions=scraper.instructions_list(),
        source_url=response.url,
        image=scraper.image(),
        metadata=metadata,
    )
