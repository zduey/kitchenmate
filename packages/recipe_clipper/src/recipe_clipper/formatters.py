"""Recipe output formatters."""

from recipe_clipper.models import Recipe, RecipeMetadata, Ingredient


# Helper functions for formatting


def _format_ingredient(ingredient: Ingredient) -> str:
    """Get ingredient display text."""
    return ingredient.display_text or ingredient.name


def _format_metadata_lines(metadata: RecipeMetadata, style: str = "text") -> list[str]:
    """Format all metadata fields as lines.

    Args:
        metadata: Recipe metadata to format
        style: Format style ("text" or "markdown")

    Returns:
        List of formatted metadata lines
    """
    if not metadata:
        return []

    lines = []
    field_map = {
        "Author": metadata.author,
        "Servings": metadata.servings,
        "Prep Time": f"{metadata.prep_time} minutes" if metadata.prep_time else None,
        "Cook Time": f"{metadata.cook_time} minutes" if metadata.cook_time else None,
        "Total Time": f"{metadata.total_time} minutes" if metadata.total_time else None,
        "Categories": ", ".join(metadata.categories) if metadata.categories else None,
    }

    for key, value in field_map.items():
        if value:
            if style == "markdown":
                lines.append(f"- **{key}:** {value}")
            else:
                lines.append(f"{key}: {value}")

    return lines


def format_recipe_text(recipe: Recipe) -> str:
    """Format recipe as human-readable text."""
    lines = []

    # Title
    lines.append(f"\n{'=' * 80}")
    lines.append(recipe.title.center(80))
    lines.append("=" * 80)

    # Metadata
    metadata_lines = _format_metadata_lines(recipe.metadata, style="text")
    if metadata_lines:
        lines.append("\nMETADATA")
        lines.append("-" * 80)
        lines.extend(metadata_lines)

    # Ingredients
    lines.append("\nINGREDIENTS")
    lines.append("-" * 80)
    for ingredient in recipe.ingredients:
        lines.append(f"  • {_format_ingredient(ingredient)}")

    # Instructions
    lines.append("\nINSTRUCTIONS")
    lines.append("-" * 80)
    for i, instruction in enumerate(recipe.instructions, 1):
        lines.append(f"{i}. {instruction}")

    # Source
    if recipe.source_url:
        lines.append(f"\nSource: {recipe.source_url}")

    lines.append("")
    return "\n".join(lines)


def format_recipe_json(recipe: Recipe) -> str:
    """Format recipe as JSON."""
    return recipe.model_dump_json(indent=2, exclude_none=True)


def format_recipe_markdown(recipe: Recipe) -> str:
    """Format recipe as Markdown."""
    lines = []

    # Title (big heading)
    lines.append(f"# {recipe.title}")
    lines.append("")

    # Metadata
    metadata_lines = _format_metadata_lines(recipe.metadata, style="markdown")
    if metadata_lines:
        lines.append("## Metadata")
        lines.append("")
        lines.extend(metadata_lines)
        lines.append("")

    # Ingredients
    lines.append("## Ingredients")
    lines.append("")
    for ingredient in recipe.ingredients:
        lines.append(f"- {_format_ingredient(ingredient)}")
    lines.append("")

    # Instructions
    lines.append("## Instructions")
    lines.append("")
    for i, instruction in enumerate(recipe.instructions, 1):
        lines.append(f"{i}. {instruction}")
    lines.append("")

    # Source
    if recipe.source_url:
        lines.append("## Source")
        lines.append("")
        lines.append(f"[{recipe.source_url}]({recipe.source_url})")
        lines.append("")

    return "\n".join(lines)
