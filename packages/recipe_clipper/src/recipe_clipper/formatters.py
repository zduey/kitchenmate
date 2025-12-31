"""Recipe output formatters."""

from recipe_clipper.models import Recipe


def format_recipe_text(recipe: Recipe) -> str:
    """Format recipe as human-readable text."""
    lines = []

    # Title
    lines.append(f"\n{'=' * 80}")
    lines.append(recipe.title.center(80))
    lines.append("=" * 80)

    # Metadata
    if recipe.metadata:
        lines.append("\nMETADATA")
        lines.append("-" * 80)
        if recipe.metadata.author:
            lines.append(f"Author: {recipe.metadata.author}")
        if recipe.metadata.servings:
            lines.append(f"Servings: {recipe.metadata.servings}")
        if recipe.metadata.prep_time:
            lines.append(f"Prep Time: {recipe.metadata.prep_time} minutes")
        if recipe.metadata.cook_time:
            lines.append(f"Cook Time: {recipe.metadata.cook_time} minutes")
        if recipe.metadata.total_time:
            lines.append(f"Total Time: {recipe.metadata.total_time} minutes")
        if recipe.metadata.categories:
            lines.append(f"Categories: {', '.join(recipe.metadata.categories)}")

    # Ingredients
    lines.append("\nINGREDIENTS")
    lines.append("-" * 80)
    for ingredient in recipe.ingredients:
        display_text = ingredient.display_text
        if ingredient.display_text is None:
            display_text = f"{ingredient.amount} {ingredient.name}, {ingredient.preparation}"
        lines.append(f"  • {display_text}")

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
    if recipe.metadata:
        lines.append("## Metadata")
        lines.append("")
        if recipe.metadata.author:
            lines.append(f"- **Author:** {recipe.metadata.author}")
        if recipe.metadata.servings:
            lines.append(f"- **Servings:** {recipe.metadata.servings}")
        if recipe.metadata.prep_time:
            lines.append(f"- **Prep Time:** {recipe.metadata.prep_time} minutes")
        if recipe.metadata.cook_time:
            lines.append(f"- **Cook Time:** {recipe.metadata.cook_time} minutes")
        if recipe.metadata.total_time:
            lines.append(f"- **Total Time:** {recipe.metadata.total_time} minutes")
        if recipe.metadata.categories:
            lines.append(f"- **Categories:** {', '.join(recipe.metadata.categories)}")
        lines.append("")

    # Ingredients
    lines.append("## Ingredients")
    lines.append("")
    for ingredient in recipe.ingredients:
        display_text = ingredient.display_text
        if ingredient.display_text is None:
            display_text = f"{ingredient.amount} {ingredient.name}, {ingredient.preparation}"
        lines.append(f"- {display_text}")
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
