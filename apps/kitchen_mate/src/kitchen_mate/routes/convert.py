"""Recipe format conversion endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from recipe_clipper.formatters import format_recipe_markdown, format_recipe_text

from kitchen_mate.schemas import ConvertRequest, OutputFormat


router = APIRouter()


@router.post("/convert")
async def convert_recipe_endpoint(request: ConvertRequest) -> Response:
    """Convert a recipe to text or markdown format.

    Returns the formatted recipe as a downloadable file.
    """
    if request.format == OutputFormat.json:
        raise HTTPException(
            status_code=400,
            detail="JSON format not supported. Use the recipe data directly.",
        )

    if request.format == OutputFormat.text:
        content = format_recipe_text(request.recipe)
        content_type = "text/plain"
        extension = "txt"
    else:
        content = format_recipe_markdown(request.recipe)
        content_type = "text/markdown"
        extension = "md"

    filename = f"recipe.{extension}"
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
