"""Command-line interface for recipe clipper."""

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from dotenv import load_dotenv

from recipe_clipper.clipper import clip_recipe
from recipe_clipper.parsers.llm_parser import (
    parse_recipe_from_image,
    parse_recipe_from_document,
)
from recipe_clipper.formatters import (
    format_recipe_text,
    format_recipe_json,
    format_recipe_markdown,
)
from recipe_clipper.exceptions import RecipeClipperError

load_dotenv()


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


# Helper functions for common CLI operations


def _format_recipe(recipe, format: OutputFormat) -> str:
    """Format recipe based on output format."""
    if format == OutputFormat.json:
        return format_recipe_json(recipe)
    elif format == OutputFormat.markdown:
        return format_recipe_markdown(recipe)
    else:
        return format_recipe_text(recipe)


def _write_output(output_text: str, output: Optional[Path]) -> None:
    """Write output to file or stdout."""
    if output:
        output.write_text(output_text)
        console.print(f"[green]✓[/green] Recipe saved to {output}")
    else:
        console.print(output_text)


def _handle_recipe_extraction(
    extract_func, source_description: str, format: OutputFormat, output: Optional[Path]
) -> None:
    """Common handler for all recipe extraction commands."""
    try:
        with console.status(f"[bold blue]{source_description}..."):
            recipe = extract_func()

        output_text = _format_recipe(recipe, format)
        _write_output(output_text, output)

    except RecipeClipperError as e:
        console.print(f"[red]Error:[/red] {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", file=sys.stderr)
        raise typer.Exit(code=1)


def _validate_file_exists(path: Path, file_type: str) -> None:
    """Validate that a file exists."""
    if not path.exists():
        console.print(f"[red]Error:[/red] {file_type} file not found: {path}", file=sys.stderr)
        raise typer.Exit(code=1)


def _require_api_key(api_key: Optional[str], operation: str) -> str:
    """Ensure API key is provided, exit if not."""
    if not api_key:
        console.print(
            f"[red]Error:[/red] API key is required for {operation}. "
            "Set ANTHROPIC_API_KEY environment variable or use --api-key option.",
            file=sys.stderr,
        )
        raise typer.Exit(code=1)
    return api_key


@app.command()
def clip_webpage(
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
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        envvar="ANTHROPIC_API_KEY",
        help="Anthropic API key for LLM fallback (can also use ANTHROPIC_API_KEY env var)",
    ),
    use_llm_fallback: bool = typer.Option(
        True,
        "--use-llm-fallback/--no-llm-fallback",
        help="Use LLM fallback if recipe-scrapers fails",
    ),
):
    """
    Extract a recipe from a URL.

    Examples:

        recipe-clipper clip-webpage https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/

        recipe-clipper clip-webpage https://example.com/recipe --format json --output recipe.json

        recipe-clipper clip-webpage https://example.com/recipe --format markdown --output recipe.md

        recipe-clipper clip-webpage https://unsupported-site.com/recipe --api-key sk-ant-... --use-llm-fallback
    """
    _handle_recipe_extraction(
        extract_func=lambda: clip_recipe(
            url, api_key=api_key, use_llm_fallback=use_llm_fallback, timeout=timeout
        ),
        source_description=f"Fetching recipe from {url}",
        format=format,
        output=output,
    )


@app.command()
def clip_image(
    image_path: Path = typer.Argument(..., help="Path to the recipe image file"),
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
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        envvar="ANTHROPIC_API_KEY",
        help="Anthropic API key (required, can also use ANTHROPIC_API_KEY env var)",
    ),
    model: str = typer.Option(
        "claude-sonnet-4-5",
        "--model",
        "-m",
        help="Claude model to use",
    ),
):
    """
    Extract a recipe from an image (e.g., cookbook photo, recipe card).

    This command uses Claude's vision API to extract recipe text from images.
    Requires an Anthropic API key.

    Examples:

        recipe-clipper clip-image recipe.jpg

        recipe-clipper clip-image cookbook-page.png --format json --output recipe.json

        recipe-clipper clip-image recipe-card.jpg --api-key sk-ant-... --format markdown
    """
    api_key = _require_api_key(api_key, "image parsing")
    _validate_file_exists(image_path, "Image")

    _handle_recipe_extraction(
        extract_func=lambda: parse_recipe_from_image(image_path, api_key, model=model),
        source_description=f"Extracting recipe from {image_path}",
        format=format,
        output=output,
    )


@app.command()
def clip_document(
    document_path: Path = typer.Argument(..., help="Path to the recipe document file"),
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
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        envvar="ANTHROPIC_API_KEY",
        help="Anthropic API key (required, can also use ANTHROPIC_API_KEY env var)",
    ),
    model: str = typer.Option(
        "claude-sonnet-4-5",
        "--model",
        "-m",
        help="Claude model to use",
    ),
):
    """
    Extract a recipe from a document (PDF, Word, text, markdown).

    This command uses Claude's document API to extract recipe text from various
    document formats. Requires an Anthropic API key.

    Supported formats: .pdf, .docx, .txt, .md

    Examples:

        recipe-clipper clip-document recipe.pdf

        recipe-clipper clip-document cookbook.docx --format json --output recipe.json

        recipe-clipper clip-document recipe.txt --api-key sk-ant-... --format markdown
    """
    api_key = _require_api_key(api_key, "document parsing")
    _validate_file_exists(document_path, "Document")

    _handle_recipe_extraction(
        extract_func=lambda: parse_recipe_from_document(document_path, api_key, model=model),
        source_description=f"Extracting recipe from {document_path}",
        format=format,
        output=output,
    )


if __name__ == "__main__":
    app()
