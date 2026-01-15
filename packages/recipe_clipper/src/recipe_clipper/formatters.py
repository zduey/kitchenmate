"""Recipe output formatters."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from recipe_clipper.models import Recipe, RecipeMetadata, Ingredient

if TYPE_CHECKING:
    from PIL import Image as PILImage


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


# Export format helpers


def _generate_recipe_html(recipe: Recipe, include_image: bool = True) -> str:
    """Generate styled HTML for recipe export.

    Args:
        recipe: Recipe to format
        include_image: Whether to include recipe image if available

    Returns:
        HTML string with embedded styles
    """
    metadata_html = ""
    if recipe.metadata:
        metadata_items = []
        if recipe.metadata.author:
            metadata_items.append(f"<li><strong>Author:</strong> {recipe.metadata.author}</li>")
        if recipe.metadata.servings:
            metadata_items.append(f"<li><strong>Servings:</strong> {recipe.metadata.servings}</li>")
        if recipe.metadata.prep_time:
            metadata_items.append(
                f"<li><strong>Prep Time:</strong> {recipe.metadata.prep_time} minutes</li>"
            )
        if recipe.metadata.cook_time:
            metadata_items.append(
                f"<li><strong>Cook Time:</strong> {recipe.metadata.cook_time} minutes</li>"
            )
        if recipe.metadata.total_time:
            metadata_items.append(
                f"<li><strong>Total Time:</strong> {recipe.metadata.total_time} minutes</li>"
            )
        if recipe.metadata.categories:
            metadata_items.append(
                f"<li><strong>Categories:</strong> {', '.join(recipe.metadata.categories)}</li>"
            )
        if metadata_items:
            metadata_html = f"<ul class='metadata'>{''.join(metadata_items)}</ul>"

    image_html = ""
    if include_image and recipe.image:
        image_html = f'<img src="{recipe.image}" alt="{recipe.title}" class="recipe-image" />'

    ingredients_html = "\n".join(
        f"<li>{_format_ingredient(ing)}</li>" for ing in recipe.ingredients
    )

    instructions_html = "\n".join(f"<li>{instruction}</li>" for instruction in recipe.instructions)

    source_html = ""
    if recipe.source_url:
        source_html = f'<p class="source"><strong>Source:</strong> <a href="{recipe.source_url}">{recipe.source_url}</a></p>'

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 24px;
        }}
        .recipe-image {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .metadata {{
            list-style: none;
            padding: 0;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px 20px;
        }}
        .metadata li {{
            margin: 5px 0;
        }}
        ul, ol {{
            padding-left: 20px;
        }}
        li {{
            margin: 8px 0;
        }}
        .source {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 0.9em;
        }}
        .source a {{
            color: #3498db;
        }}
    </style>
</head>
<body>
    <h1>{recipe.title}</h1>
    {image_html}
    {metadata_html}
    <h2>Ingredients</h2>
    <ul>{ingredients_html}</ul>
    <h2>Instructions</h2>
    <ol>{instructions_html}</ol>
    {source_html}
</body>
</html>"""


def _download_image(url: str, timeout: int = 10) -> PILImage.Image | None:
    """Download an image from URL.

    Args:
        url: Image URL to download
        timeout: Request timeout in seconds

    Returns:
        PIL Image object or None if download fails
    """
    try:
        import httpx
        from PIL import Image

        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content))
    except Exception:
        return None


def _wrap_text(text: str, font: "PILImage.ImageFont", max_width: int) -> list[str]:
    """Wrap text to fit within a given width.

    Args:
        text: Text to wrap
        font: PIL ImageFont to use for measuring
        max_width: Maximum width in pixels

    Returns:
        List of wrapped lines
    """
    from PIL import ImageDraw, Image

    # Create a temporary image for text measurement
    tmp_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(tmp_img)

    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines if lines else [text]


def _render_recipe_image(
    recipe: Recipe,
    width: int = 800,
    background_color: tuple[int, int, int] = (255, 255, 255),
) -> PILImage.Image:
    """Render a recipe as an image using Pillow.

    Args:
        recipe: Recipe to render
        width: Image width in pixels
        background_color: RGB background color

    Returns:
        PIL Image object
    """
    from PIL import Image, ImageDraw, ImageFont

    # Configuration
    padding = 40
    line_height = 24
    title_line_height = 40
    title_size = 32
    heading_size = 24
    text_size = 16
    content_width = width - (padding * 2)

    # Try to get a font, fall back to default
    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", title_size
        )
        heading_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", heading_size
        )
        text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", text_size)
    except OSError:
        title_font = ImageFont.load_default()
        heading_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Pre-wrap all text to calculate accurate height
    title_lines = _wrap_text(recipe.title, title_font, content_width)

    ingredient_lines_list = []
    for ingredient in recipe.ingredients:
        text = f"• {_format_ingredient(ingredient)}"
        wrapped = _wrap_text(text, text_font, content_width - 10)
        ingredient_lines_list.append(wrapped)

    instruction_lines_list = []
    for i, instruction in enumerate(recipe.instructions, 1):
        text = f"{i}. {instruction}"
        wrapped = _wrap_text(text, text_font, content_width - 10)
        instruction_lines_list.append(wrapped)

    metadata_lines = []
    if recipe.metadata:
        metadata_lines = _format_metadata_lines(recipe.metadata, style="text")

    source_lines = []
    if recipe.source_url:
        source_lines = _wrap_text(f"Source: {recipe.source_url}", text_font, content_width)

    # Download recipe image if available
    recipe_image = None
    recipe_image_height = 0
    if recipe.image:
        recipe_image = _download_image(str(recipe.image))
        if recipe_image:
            # Scale image to fit width
            aspect_ratio = recipe_image.height / recipe_image.width
            recipe_image = recipe_image.resize(
                (content_width, int(content_width * aspect_ratio)),
                Image.Resampling.LANCZOS,
            )
            recipe_image_height = recipe_image.height + 20

    # Calculate total height
    height = padding  # Top padding
    height += len(title_lines) * title_line_height + 10  # Title
    height += recipe_image_height  # Recipe image
    if metadata_lines:
        height += heading_size + 10  # Metadata heading
        height += len(metadata_lines) * line_height + 15
    height += heading_size + 10  # Ingredients heading
    for lines in ingredient_lines_list:
        height += len(lines) * line_height
    height += 15
    height += heading_size + 10  # Instructions heading
    for lines in instruction_lines_list:
        height += len(lines) * line_height + 8  # Extra spacing between instructions
    height += 15
    if source_lines:
        height += len(source_lines) * line_height + 10
    height += padding  # Bottom padding

    # Create image
    img = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(img)
    y = padding

    # Draw title
    for line in title_lines:
        draw.text((padding, y), line, fill=(44, 62, 80), font=title_font)
        y += title_line_height
    y += 10

    # Draw recipe image
    if recipe_image:
        img.paste(recipe_image, (padding, y))
        y += recipe_image_height

    # Draw metadata
    if metadata_lines:
        draw.text((padding, y), "Metadata", fill=(52, 73, 94), font=heading_font)
        y += heading_size + 10
        for line in metadata_lines:
            draw.text((padding + 10, y), line, fill=(100, 100, 100), font=text_font)
            y += line_height
        y += 15

    # Draw ingredients
    draw.text((padding, y), "Ingredients", fill=(52, 73, 94), font=heading_font)
    y += heading_size + 10
    for lines in ingredient_lines_list:
        for line in lines:
            draw.text((padding + 10, y), line, fill=(51, 51, 51), font=text_font)
            y += line_height
    y += 15

    # Draw instructions
    draw.text((padding, y), "Instructions", fill=(52, 73, 94), font=heading_font)
    y += heading_size + 10
    for lines in instruction_lines_list:
        for line in lines:
            draw.text((padding + 10, y), line, fill=(51, 51, 51), font=text_font)
            y += line_height
        y += 8  # Extra spacing between instructions
    y += 15

    # Draw source
    if source_lines:
        for line in source_lines:
            draw.text((padding, y), line, fill=(100, 100, 100), font=text_font)
            y += line_height

    return img


def format_recipe_pdf(recipe: Recipe) -> bytes:
    """Format recipe as PDF.

    Requires the 'export' optional dependency: pip install recipe-clipper[export]

    Args:
        recipe: Recipe to format

    Returns:
        PDF file contents as bytes
    """
    try:
        from weasyprint import HTML
    except ImportError as e:
        raise ImportError(
            "PDF export requires weasyprint. Install with: pip install recipe-clipper[export]"
        ) from e

    html_content = _generate_recipe_html(recipe, include_image=True)
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


def format_recipe_png(recipe: Recipe, width: int = 800) -> bytes:
    """Format recipe as PNG image.

    Requires the 'export' optional dependency: pip install recipe-clipper[export]

    Args:
        recipe: Recipe to format
        width: Image width in pixels

    Returns:
        PNG file contents as bytes
    """
    img = _render_recipe_image(recipe, width=width)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def format_recipe_jpeg(recipe: Recipe, width: int = 800, quality: int = 85) -> bytes:
    """Format recipe as JPEG image.

    Requires the 'export' optional dependency: pip install recipe-clipper[export]

    Args:
        recipe: Recipe to format
        width: Image width in pixels
        quality: JPEG quality (1-100)

    Returns:
        JPEG file contents as bytes
    """
    img = _render_recipe_image(recipe, width=width)
    # Convert to RGB if necessary (JPEG doesn't support alpha)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def format_recipe_webp(recipe: Recipe, width: int = 800, quality: int = 85) -> bytes:
    """Format recipe as WebP image.

    Requires the 'export' optional dependency: pip install recipe-clipper[export]

    Args:
        recipe: Recipe to format
        width: Image width in pixels
        quality: WebP quality (1-100)

    Returns:
        WebP file contents as bytes
    """
    img = _render_recipe_image(recipe, width=width)
    buffer = io.BytesIO()
    img.save(buffer, format="WEBP", quality=quality)
    return buffer.getvalue()


def format_recipe_svg(recipe: Recipe, width: int = 800) -> str:
    """Format recipe as SVG.

    Args:
        recipe: Recipe to format
        width: SVG width in pixels

    Returns:
        SVG file contents as string
    """
    # Configuration
    padding = 40
    line_height = 24
    title_size = 28
    heading_size = 20
    text_size = 14
    content_width = width - (padding * 2)

    # Calculate height needed
    y = padding
    elements = []

    # Title
    elements.append(
        f'<text x="{padding}" y="{y + title_size}" '
        f'font-family="sans-serif" font-size="{title_size}" font-weight="bold" fill="#2c3e50">'
        f"{_escape_svg(recipe.title)}</text>"
    )
    y += title_size + 30

    # Recipe image placeholder (SVG can't easily embed external images)
    if recipe.image:
        elements.append(
            f'<image x="{padding}" y="{y}" width="{content_width}" height="200" '
            f'href="{recipe.image}" preserveAspectRatio="xMidYMid meet" />'
        )
        y += 220

    # Metadata
    if recipe.metadata:
        metadata_lines = _format_metadata_lines(recipe.metadata, style="text")
        if metadata_lines:
            elements.append(
                f'<text x="{padding}" y="{y + heading_size}" '
                f'font-family="sans-serif" font-size="{heading_size}" font-weight="bold" fill="#34495e">'
                f"Metadata</text>"
            )
            y += heading_size + 15
            for line in metadata_lines:
                elements.append(
                    f'<text x="{padding + 10}" y="{y + text_size}" '
                    f'font-family="sans-serif" font-size="{text_size}" fill="#666">'
                    f"{_escape_svg(line)}</text>"
                )
                y += line_height
            y += 15

    # Ingredients
    elements.append(
        f'<text x="{padding}" y="{y + heading_size}" '
        f'font-family="sans-serif" font-size="{heading_size}" font-weight="bold" fill="#34495e">'
        f"Ingredients</text>"
    )
    y += heading_size + 15
    for ingredient in recipe.ingredients:
        text = f"• {_format_ingredient(ingredient)}"
        elements.append(
            f'<text x="{padding + 10}" y="{y + text_size}" '
            f'font-family="sans-serif" font-size="{text_size}" fill="#333">'
            f"{_escape_svg(text)}</text>"
        )
        y += line_height
    y += 15

    # Instructions
    elements.append(
        f'<text x="{padding}" y="{y + heading_size}" '
        f'font-family="sans-serif" font-size="{heading_size}" font-weight="bold" fill="#34495e">'
        f"Instructions</text>"
    )
    y += heading_size + 15
    for i, instruction in enumerate(recipe.instructions, 1):
        # Truncate long instructions
        text = f"{i}. {instruction}"
        if len(text) > 100:
            text = text[:97] + "..."
        elements.append(
            f'<text x="{padding + 10}" y="{y + text_size}" '
            f'font-family="sans-serif" font-size="{text_size}" fill="#333">'
            f"{_escape_svg(text)}</text>"
        )
        y += line_height * 1.5
    y += 15

    # Source
    if recipe.source_url:
        elements.append(
            f'<text x="{padding}" y="{y + text_size}" '
            f'font-family="sans-serif" font-size="{text_size}" fill="#666">'
            f"Source: {_escape_svg(str(recipe.source_url))}</text>"
        )
        y += line_height

    height = y + padding

    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <rect width="100%" height="100%" fill="white"/>
    {"".join(elements)}
</svg>'''

    return svg_content


def _escape_svg(text: str) -> str:
    """Escape special characters for SVG text elements."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
