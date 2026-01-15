"""Recipe format conversion endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from recipe_clipper.formatters import (
    format_recipe_jpeg,
    format_recipe_markdown,
    format_recipe_pdf,
    format_recipe_png,
    format_recipe_svg,
    format_recipe_text,
    format_recipe_webp,
)

from kitchen_mate.schemas import ConvertRequest, OutputFormat


router = APIRouter()


@router.post("/convert")
async def convert_recipe_endpoint(request: ConvertRequest) -> Response:
    """Convert a recipe to various output formats.

    Returns the formatted recipe as a downloadable file.
    """
    if request.format == OutputFormat.json:
        raise HTTPException(
            status_code=400,
            detail="JSON format not supported. Use the recipe data directly.",
        )

    content: str | bytes
    content_type: str
    extension: str

    match request.format:
        case OutputFormat.text:
            content = format_recipe_text(request.recipe)
            content_type = "text/plain"
            extension = "txt"
        case OutputFormat.markdown:
            content = format_recipe_markdown(request.recipe)
            content_type = "text/markdown"
            extension = "md"
        case OutputFormat.pdf:
            content = format_recipe_pdf(request.recipe)
            content_type = "application/pdf"
            extension = "pdf"
        case OutputFormat.jpeg:
            content = format_recipe_jpeg(request.recipe)
            content_type = "image/jpeg"
            extension = "jpg"
        case OutputFormat.png:
            content = format_recipe_png(request.recipe)
            content_type = "image/png"
            extension = "png"
        case OutputFormat.webp:
            content = format_recipe_webp(request.recipe)
            content_type = "image/webp"
            extension = "webp"
        case OutputFormat.svg:
            content = format_recipe_svg(request.recipe)
            content_type = "image/svg+xml"
            extension = "svg"
        case _:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {request.format}",
            )

    filename = f"recipe.{extension}"
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
