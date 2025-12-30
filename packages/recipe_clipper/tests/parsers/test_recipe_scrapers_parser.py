"""Tests for recipe-scrapers parser."""

from unittest.mock import Mock, patch
import pytest

from recipe_clipper.parsers.recipe_scrapers_parser import parse_with_recipe_scrapers
from recipe_clipper.http import HttpResponse
from recipe_clipper.models import Recipe
from recipe_clipper.exceptions import RecipeParsingError


def test_parse_with_recipe_scrapers_unit():
    """Unit test with mocked scraper."""
    # Arrange
    response = HttpResponse(
        content="<html>mock html</html>",
        status_code=200,
        url="https://example.com/recipe",
    )

    mock_scraper = Mock()
    mock_scraper.title.return_value = "Mock Recipe Title"
    mock_scraper.ingredients.return_value = [
        "2 cups flour",
        "1 cup sugar",
        "3 eggs",
    ]
    mock_scraper.instructions_list.return_value = [
        "Mix dry ingredients",
        "Add wet ingredients",
        "Bake at 350F for 30 minutes",
    ]
    mock_scraper.author.return_value = "Test Chef"
    mock_scraper.yields.return_value = "8"
    mock_scraper.prep_time.return_value = 15
    mock_scraper.cook_time.return_value = 30
    mock_scraper.total_time.return_value = 45
    mock_scraper.category.return_value = "Dessert"
    mock_scraper.image.return_value = "https://example.com/image.jpg"

    # Act
    with patch("recipe_clipper.parsers.recipe_scrapers_parser.scrape_html") as mock_scrape:
        mock_scrape.return_value = mock_scraper
        recipe = parse_with_recipe_scrapers(response)

    # Assert
    assert isinstance(recipe, Recipe)
    assert recipe.title == "Mock Recipe Title"
    assert len(recipe.ingredients) == 3
    assert recipe.ingredients[0].name == "2 cups flour"
    assert len(recipe.instructions) == 3
    assert recipe.instructions[0] == "Mix dry ingredients"
    assert str(recipe.source_url) == "https://example.com/recipe"
    assert str(recipe.image) == "https://example.com/image.jpg"

    # Verify metadata
    assert recipe.metadata is not None
    assert recipe.metadata.author == "Test Chef"
    assert recipe.metadata.servings == "8"
    assert recipe.metadata.prep_time == 15
    assert recipe.metadata.cook_time == 30
    assert recipe.metadata.total_time == 45
    assert recipe.metadata.categories == ["Dessert"]

    # Verify scrape_html was called correctly
    mock_scrape.assert_called_once_with(response.content, response.url, supported_only=False)


def test_parse_with_recipe_scrapers_website_not_implemented():
    """Test handling of scraper creation failure."""
    from recipe_scrapers import WebsiteNotImplementedError

    response = HttpResponse(
        content="<html>unsupported site</html>",
        status_code=200,
        url="https://unsupported.com/recipe",
    )

    with patch("recipe_clipper.parsers.recipe_scrapers_parser.scrape_html") as mock_scrape:
        mock_scrape.side_effect = WebsiteNotImplementedError("Not supported")

        with pytest.raises(RecipeParsingError) as exc_info:
            parse_with_recipe_scrapers(response)

        assert "Failed to create scraper" in str(exc_info.value)
        assert "https://unsupported.com/recipe" in str(exc_info.value)


def test_parse_with_recipe_scrapers_parsing_error():
    """Test handling of parsing errors."""
    response = HttpResponse(
        content="<html>malformed</html>",
        status_code=200,
        url="https://example.com/recipe",
    )

    with patch("recipe_clipper.parsers.recipe_scrapers_parser.scrape_html") as mock_scrape:
        mock_scrape.side_effect = ValueError("Invalid HTML structure")

        with pytest.raises(RecipeParsingError) as exc_info:
            parse_with_recipe_scrapers(response)

        assert "Failed to create scraper" in str(exc_info.value)
        assert "https://example.com/recipe" in str(exc_info.value)


def test_parse_with_recipe_scrapers_no_category():
    """Test handling when category is None."""
    response = HttpResponse(
        content="<html>mock html</html>",
        status_code=200,
        url="https://example.com/recipe",
    )

    mock_scraper = Mock()
    mock_scraper.title.return_value = "Recipe Without Category"
    mock_scraper.ingredients.return_value = ["1 cup water"]
    mock_scraper.instructions_list.return_value = ["Boil water"]
    mock_scraper.author.return_value = "Chef"
    mock_scraper.yields.return_value = "1"
    mock_scraper.prep_time.return_value = 5
    mock_scraper.cook_time.return_value = 10
    mock_scraper.total_time.return_value = 15
    mock_scraper.category.return_value = None  # No category
    mock_scraper.image.return_value = "https://example.com/image.jpg"

    with patch("recipe_clipper.parsers.recipe_scrapers_parser.scrape_html") as mock_scrape:
        mock_scrape.return_value = mock_scraper
        recipe = parse_with_recipe_scrapers(response)

    assert recipe.metadata is not None
    assert recipe.metadata.categories is None


@pytest.mark.integration
def test_parse_with_recipe_scrapers_integration():
    """Integration test using actual HTML with schema.org markup (no mocking)."""
    # Real HTML with schema.org Recipe markup
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chocolate Chip Cookies Recipe</title>
    </head>
    <body>
        <div itemscope itemtype="http://schema.org/Recipe">
            <h1 itemprop="name">Chocolate Chip Cookies</h1>
            <img itemprop="image" src="https://example.com/cookies.jpg" alt="Cookies"/>
            <p itemprop="author">Jane Baker</p>
            <p>Yield: <span itemprop="recipeYield">24 cookies</span></p>
            <p>Prep time: <meta itemprop="prepTime" content="PT15M">15 minutes</p>
            <p>Cook time: <meta itemprop="cookTime" content="PT12M">12 minutes</p>
            <p>Total time: <meta itemprop="totalTime" content="PT27M">27 minutes</p>
            <p>Category: <span itemprop="recipeCategory">Dessert</span></p>

            <h2>Ingredients:</h2>
            <ul>
                <li itemprop="recipeIngredient">2 1/4 cups all-purpose flour</li>
                <li itemprop="recipeIngredient">1 tsp baking soda</li>
                <li itemprop="recipeIngredient">1 tsp salt</li>
                <li itemprop="recipeIngredient">1 cup butter, softened</li>
                <li itemprop="recipeIngredient">3/4 cup granulated sugar</li>
                <li itemprop="recipeIngredient">2 cups chocolate chips</li>
            </ul>

            <h2>Instructions:</h2>
            <ol itemprop="recipeInstructions">
                <li>Preheat oven to 375 degrees F</li>
                <li>Combine flour, baking soda and salt in small bowl</li>
                <li>Beat butter and sugars in large mixer bowl until creamy</li>
                <li>Stir in flour mixture and chocolate chips</li>
                <li>Drop by rounded tablespoon onto ungreased baking sheets</li>
                <li>Bake for 9 to 11 minutes or until golden brown</li>
            </ol>
        </div>
    </body>
    </html>
    """

    response = HttpResponse(
        content=html_content,
        status_code=200,
        url="https://www.allrecipes.com/recipe/chocolate-chip-cookies",
    )

    # Act - call actual parser without mocking
    recipe = parse_with_recipe_scrapers(response)

    # Assert - verify the recipe was parsed correctly
    assert isinstance(recipe, Recipe)
    assert recipe.title == "Chocolate Chip Cookies"
    assert str(recipe.source_url) == "https://www.allrecipes.com/recipe/chocolate-chip-cookies"
    assert str(recipe.image) == "https://example.com/cookies.jpg"

    # Verify ingredients
    assert len(recipe.ingredients) == 6
    assert recipe.ingredients[0].name == "2 1/4 cups all-purpose flour"
    assert recipe.ingredients[5].name == "2 cups chocolate chips"

    # Verify instructions
    assert len(recipe.instructions) == 6
    assert "Preheat oven to 375 degrees F" in recipe.instructions[0]
    assert "Bake for 9 to 11 minutes" in recipe.instructions[5]

    # Verify metadata
    assert recipe.metadata is not None
    assert recipe.metadata.author == "Jane Baker"
    assert recipe.metadata.servings == "24 cookies"
    assert recipe.metadata.prep_time == 15
    assert recipe.metadata.cook_time == 12
    assert recipe.metadata.total_time == 27
    assert recipe.metadata.categories == ["Dessert"]
