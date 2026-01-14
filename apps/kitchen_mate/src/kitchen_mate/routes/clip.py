"""Recipe clipping endpoint."""

from __future__ import annotations

import asyncio
import json
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from recipe_clipper.exceptions import (
    LLMError,
    NetworkError,
    RecipeClipperError,
    RecipeNotFoundError,
    RecipeParsingError,
)
from recipe_clipper.formatters import format_recipe_json
from recipe_clipper.http import fetch_url
from recipe_clipper.parsers.recipe_scrapers_parser import parse_with_recipe_scrapers

from kitchen_mate.config import Settings, get_settings, is_ip_allowed
from kitchen_mate.schemas import ClipRequest

router = APIRouter()


def _sse_event(data: dict) -> str:
    """Format a dict as an SSE event."""
    return f"data: {json.dumps(data)}\n\n"


async def _stream_clip_recipe(
    url: str,
    timeout: int,
    use_llm_fallback: bool,
    api_key: str | None,
) -> AsyncGenerator[str, None]:
    """Stream recipe extraction with progress updates."""
    try:
        # Stage 1: Fetching
        yield _sse_event({"stage": "fetching", "message": "Fetching page..."})
        response = await asyncio.to_thread(fetch_url, url, timeout=timeout)

        # Stage 2: Parsing
        yield _sse_event({"stage": "parsing", "message": "Parsing recipe..."})
        try:
            recipe = await asyncio.to_thread(parse_with_recipe_scrapers, response)
        except RecipeParsingError:
            if not use_llm_fallback:
                raise

            # Stage 3: LLM fallback
            yield _sse_event({"stage": "llm", "message": "Using AI extraction..."})
            from recipe_clipper.parsers.llm_parser import parse_with_claude

            recipe = await asyncio.to_thread(parse_with_claude, url, api_key)

        # Stage 4: Complete
        yield _sse_event(
            {
                "stage": "complete",
                "recipe": json.loads(format_recipe_json(recipe)),
            }
        )

    except RecipeNotFoundError as error:
        yield _sse_event({"stage": "error", "message": str(error), "status": 404})
    except NetworkError as error:
        yield _sse_event(
            {"stage": "error", "message": f"Failed to fetch URL: {error}", "status": 502}
        )
    except (RecipeParsingError, LLMError) as error:
        yield _sse_event(
            {"stage": "error", "message": f"Failed to parse recipe: {error}", "status": 500}
        )
    except RecipeClipperError as error:
        yield _sse_event({"stage": "error", "message": str(error), "status": 500})


@router.post("/clip")
async def clip_recipe_endpoint(
    clip_request: ClipRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Extract a recipe from a URL.

    Returns the recipe data as JSON. If stream=true, returns Server-Sent Events
    with progress updates.
    """
    api_key = settings.anthropic_api_key if clip_request.use_llm_fallback else None

    if clip_request.use_llm_fallback and not api_key:
        raise HTTPException(
            status_code=400,
            detail="LLM fallback requires ANTHROPIC_API_KEY environment variable",
        )

    if clip_request.use_llm_fallback:
        client_ip = request.client.host if request.client else None
        if not client_ip or not is_ip_allowed(client_ip, settings.llm_allowed_ips):
            raise HTTPException(
                status_code=403,
                detail="LLM fallback not allowed from this IP address",
            )

    if clip_request.stream:
        return StreamingResponse(
            _stream_clip_recipe(
                str(clip_request.url),
                clip_request.timeout,
                clip_request.use_llm_fallback,
                api_key,
            ),
            media_type="text/event-stream",
        )

    # Non-streaming: use the same logic but without SSE
    try:
        response = await asyncio.to_thread(
            fetch_url, str(clip_request.url), timeout=clip_request.timeout
        )
        try:
            recipe = await asyncio.to_thread(parse_with_recipe_scrapers, response)
        except RecipeParsingError:
            if not clip_request.use_llm_fallback:
                raise
            from recipe_clipper.parsers.llm_parser import parse_with_claude

            recipe = await asyncio.to_thread(parse_with_claude, str(clip_request.url), api_key)
    except RecipeNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except NetworkError as error:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {error}") from error
    except (RecipeParsingError, LLMError) as error:
        raise HTTPException(status_code=500, detail=f"Failed to parse recipe: {error}") from error
    except RecipeClipperError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    content = format_recipe_json(recipe)
    return Response(content=content, media_type="application/json")
