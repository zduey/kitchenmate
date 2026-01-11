"""Recipe clipping endpoint."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse

from recipe_clipper import clip_recipe
from recipe_clipper.exceptions import (
    LLMError,
    NetworkError,
    RecipeClipperError,
    RecipeNotFoundError,
    RecipeParsingError,
)
from recipe_clipper.formatters import (
    format_recipe_json,
    format_recipe_markdown,
    format_recipe_text,
)

from kitchen_mate.config import Settings, get_settings
from kitchen_mate.schemas import ClipRequest, OutputFormat

router = APIRouter()


def _get_content_type(output_format: OutputFormat) -> str:
    """Get the content type for a given output format."""
    content_types = {
        OutputFormat.text: "text/plain",
        OutputFormat.json: "application/json",
        OutputFormat.markdown: "text/markdown",
    }
    return content_types[output_format]


def _get_file_extension(output_format: OutputFormat) -> str:
    """Get the file extension for a given output format."""
    extensions = {
        OutputFormat.text: "txt",
        OutputFormat.json: "json",
        OutputFormat.markdown: "md",
    }
    return extensions[output_format]


@router.post("/clip")
async def clip_recipe_endpoint(
    request: ClipRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Extract a recipe from a URL.

    Returns the recipe data in the requested format. If download=true,
    returns the response as a downloadable file.
    """
    api_key = settings.anthropic_api_key if request.use_llm_fallback else None

    if request.use_llm_fallback and not api_key:
        raise HTTPException(
            status_code=400,
            detail="LLM fallback requires ANTHROPIC_API_KEY environment variable",
        )

    try:
        recipe = await asyncio.to_thread(
            clip_recipe,
            str(request.url),
            api_key=api_key,
            use_llm_fallback=request.use_llm_fallback,
            timeout=request.timeout,
        )
    except RecipeNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except NetworkError as error:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {error}") from error
    except (RecipeParsingError, LLMError) as error:
        raise HTTPException(status_code=500, detail=f"Failed to parse recipe: {error}") from error
    except RecipeClipperError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    formatters = {
        OutputFormat.text: format_recipe_text,
        OutputFormat.json: format_recipe_json,
        OutputFormat.markdown: format_recipe_markdown,
    }
    content = formatters[request.format](recipe)
    content_type = _get_content_type(request.format)

    if request.download:
        extension = _get_file_extension(request.format)
        filename = f"recipe.{extension}"
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if request.format == OutputFormat.json:
        return Response(content=content, media_type=content_type)

    return PlainTextResponse(content=content, media_type=content_type)
