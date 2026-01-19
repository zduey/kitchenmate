"""Recipe clipping endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from recipe_clipper.exceptions import (
    LLMError,
    NetworkError,
    RecipeClipperError,
    RecipeNotFoundError,
    RecipeParsingError,
)
from recipe_clipper.models import Recipe

from kitchen_mate.config import Settings, get_settings
from kitchen_mate.db import get_cached_recipe, store_recipe, update_recipe
from kitchen_mate.extraction import LLMNotAllowedError, extract_recipe, get_client_ip
from kitchen_mate.schemas import ClipRequest, ClipResponse, Parser


router = APIRouter()


@router.post("/clip")
async def clip_recipe(
    clip_request: ClipRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClipResponse:
    """Extract a recipe from a URL."""
    url = str(clip_request.url)
    client_ip = get_client_ip(request)

    try:
        # Try cache first (unless force_refresh)
        if settings.cache_enabled and not clip_request.force_refresh:
            cached = _get_from_cache(url, clip_request.force_llm)
            if cached:
                return ClipResponse(recipe=cached.recipe, cached=True)

        # Extract the recipe
        recipe, parsed_with, content_hash, content_changed = await extract_recipe(
            url=url,
            timeout=clip_request.timeout,
            use_llm_fallback=clip_request.use_llm_fallback,
            api_key=settings.anthropic_api_key,
            client_ip=client_ip,
            allowed_ips=settings.llm_allowed_ips,
            force_llm=clip_request.force_llm,
            check_content_changed=clip_request.force_refresh and settings.cache_enabled,
        )

        # Cache the result
        if settings.cache_enabled:
            _save_to_cache(url, recipe, content_hash, parsed_with)

        return ClipResponse(recipe=recipe, cached=False, content_changed=content_changed)

    except RecipeNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except NetworkError as error:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {error}") from error
    except LLMNotAllowedError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (RecipeParsingError, LLMError) as error:
        raise HTTPException(status_code=500, detail=f"Failed to parse recipe: {error}") from error
    except RecipeClipperError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


def _get_from_cache(url: str, force_llm: bool):
    """Try to get a recipe from cache."""
    if force_llm:
        return get_cached_recipe(url, parsed_with=Parser.llm)
    return get_cached_recipe(url)


def _save_to_cache(url: str, recipe: Recipe, content_hash: str | None, parsed_with: Parser):
    """Save a recipe to cache."""
    existing = get_cached_recipe(url)
    if existing:
        update_recipe(url, recipe, content_hash, parsed_with)
    else:
        store_recipe(url, recipe, content_hash, parsed_with)
