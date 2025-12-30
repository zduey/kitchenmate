"""Parser using the recipe-scrapers library."""

from recipe_scrapers import scrape_html

from recipe_clipper.models import Recipe, Ingredient, RecipeMetadata
from recipe_clipper.http import HttpResponse
from recipe_clipper.exceptions import RecipeParsingError


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

    metadata = RecipeMetadata(
        author=scraper.author(),
        servings=scraper.yields(),
        prep_time=scraper.prep_time(),
        cook_time=scraper.cook_time(),
        total_time=scraper.total_time(),
        categories=[scraper.category()] if scraper.category() else None,
    )

    return Recipe(
        title=scraper.title(),
        ingredients=ingredients,
        instructions=scraper.instructions_list(),
        source_url=response.url,
        image=scraper.image(),
        metadata=metadata,
    )
