"""Parser using the recipe-scrapers library."""

from recipe_scrapers import scrape_html, WebsiteNotImplementedError

from recipe_clipper.models import Recipe, Ingredient, RecipeMetadata
from recipe_clipper.http import HttpResponse
from recipe_clipper.exceptions import RecipeNotFoundError, RecipeParsingError


def parse_with_recipe_scrapers(response: HttpResponse) -> Recipe:
    """
    Parse a recipe using the recipe-scrapers library.

    Args:
        response: HttpResponse containing URL and HTML content

    Returns:
        Parsed Recipe object

    Raises:
        RecipeNotFoundError: If recipe-scrapers doesn't support the URL
        RecipeParsingError: If parsing fails
    """
    try:
        scraper = scrape_html(response.content, response.url)
    except WebsiteNotImplementedError as error:
        raise RecipeNotFoundError(f"recipe-scrapers does not support {response.url}") from error
    except Exception as error:
        raise RecipeParsingError(f"Failed to create scraper for {response.url}: {error}") from error

    # Convert ingredients to our model
    ingredients = [Ingredient(name=ingredient) for ingredient in scraper.ingredients()]

    # Build metadata
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
