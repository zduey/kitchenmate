"""Command-line interface for recipe clipper."""

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from recipe_clipper.clipper import clip_recipe
from recipe_clipper.formatters import (
    format_recipe_text,
    format_recipe_json,
    format_recipe_markdown,
)
from recipe_clipper.exceptions import RecipeClipperError


app = typer.Typer(
    name="recipe-clipper",
    help="Extract recipes from websites with ease",
    add_completion=False,
)
console = Console()


class OutputFormat(str, Enum):
    """Supported output formats."""

    text = "text"
    json = "json"
    markdown = "markdown"


@app.command()
def clip(
    url: str = typer.Argument(..., help="URL of the recipe to extract"),
    format: OutputFormat = typer.Option(
        OutputFormat.text,
        "--format",
        "-f",
        help="Output format (text, json, or markdown)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (prints to stdout if not specified)",
    ),
    timeout: int = typer.Option(
        10,
        "--timeout",
        "-t",
        help="HTTP request timeout in seconds",
    ),
):
    """
    Extract a recipe from a URL.

    Examples:

        recipe-clipper clip https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/

        recipe-clipper clip https://example.com/recipe --format json --output recipe.json

        recipe-clipper clip https://example.com/recipe --format markdown --output recipe.md
    """
    try:
        # Show progress
        with console.status(f"[bold blue]Fetching recipe from {url}..."):
            recipe = clip_recipe(url, timeout=timeout)

        # Format output
        if format == OutputFormat.json:
            output_text = format_recipe_json(recipe)
        elif format == OutputFormat.markdown:
            output_text = format_recipe_markdown(recipe)
        else:
            output_text = format_recipe_text(recipe)

        # Write to file or print to stdout
        if output:
            output.write_text(output_text)
            console.print(f"[green]✓[/green] Recipe saved to {output}")
        else:
            console.print(output_text)

    except RecipeClipperError as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", file=sys.stderr)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
