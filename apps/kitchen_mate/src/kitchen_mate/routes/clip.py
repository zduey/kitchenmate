"""Recipe clipping endpoint."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from recipe_clipper.exceptions import (
    LLMError,
    NetworkError,
    RecipeClipperError,
    RecipeNotFoundError,
    RecipeParsingError,
)
from recipe_clipper.http import fetch_url
from recipe_clipper.models import Recipe
from recipe_clipper.parsers.recipe_scrapers_parser import parse_with_recipe_scrapers

from kitchen_mate.config import Settings, get_settings, is_ip_allowed
from kitchen_mate.db import get_cached_recipe, hash_content, store_recipe, update_recipe
from kitchen_mate.schemas import ClipRequest, ClipResponse, Parser


logger = logging.getLogger(__name__)
router = APIRouter()


class LLMNotAllowedError(Exception):
    """Raised when LLM fallback is not allowed for the client."""

    pass


@router.post("/clip")
async def clip_recipe(
    clip_request: ClipRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClipResponse:
    """Extract a recipe from a URL."""
    url = str(clip_request.url)
    client_ip = _get_client_ip(request)

    try:
        # Try cache first (unless force_refresh)
        if settings.cache_enabled and not clip_request.force_refresh:
            cached = _get_from_cache(url, clip_request.force_llm)
            if cached:
                return ClipResponse(recipe=cached.recipe, cached=True)

        # Extract the recipe
        recipe, parsed_with, content_hash, content_changed = await _extract_recipe(
            url=url,
            timeout=clip_request.timeout,
            force_llm=clip_request.force_llm,
            force_refresh=clip_request.force_refresh,
            use_llm_fallback=clip_request.use_llm_fallback,
            cache_enabled=settings.cache_enabled,
            api_key=settings.anthropic_api_key,
            client_ip=client_ip,
            allowed_ips=settings.llm_allowed_ips,
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


async def _extract_recipe(
    url: str,
    timeout: int,
    force_llm: bool,
    force_refresh: bool,
    use_llm_fallback: bool,
    cache_enabled: bool,
    api_key: str | None,
    client_ip: str | None,
    allowed_ips: str | None,
) -> tuple[Recipe, Parser, str | None, bool | None]:
    """Extract a recipe from a URL.

    Returns:
        Tuple of (recipe, parsed_with, content_hash, content_changed)
    """
    if force_llm:
        _check_llm_allowed(client_ip, api_key, allowed_ips)
        recipe = await _parse_with_llm(url, api_key)
        return recipe, Parser.llm, None, None

    # Fetch the page
    response = await asyncio.to_thread(fetch_url, url, timeout=timeout)
    content_hash = hash_content(response.text) if cache_enabled else None

    # Check if content changed (for force_refresh)
    content_changed = None
    if force_refresh and cache_enabled:
        cached = get_cached_recipe(url)
        if cached and cached.content_hash == content_hash:
            return cached.recipe, Parser(cached.parsed_with), content_hash, False
        content_changed = True

    # Try recipe_scrapers first
    try:
        recipe = await asyncio.to_thread(parse_with_recipe_scrapers, response)
        return recipe, Parser.recipe_scrapers, content_hash, content_changed
    except RecipeParsingError:
        if not use_llm_fallback:
            raise

    # Fall back to LLM
    _check_llm_allowed(client_ip, api_key, allowed_ips)
    recipe = await _parse_with_llm(url, api_key)
    return recipe, Parser.llm, content_hash, content_changed


async def _parse_with_llm(url: str, api_key: str | None) -> Recipe:
    """Parse a recipe using Claude."""
    from recipe_clipper.parsers.llm_parser import parse_with_claude

    return await asyncio.to_thread(parse_with_claude, url, api_key)


def _check_llm_allowed(client_ip: str | None, api_key: str | None, allowed_ips: str | None) -> None:
    """Check if LLM usage is allowed. Raises appropriate errors if not."""
    logger.info("LLM extraction attempted from IP: %s", client_ip)

    if not api_key:
        logger.warning("LLM extraction rejected: no API key configured")
        raise LLMError("LLM extraction requires ANTHROPIC_API_KEY environment variable")

    if not client_ip or not is_ip_allowed(client_ip, allowed_ips):
        logger.warning("LLM extraction rejected: IP %s not in allowed list", client_ip)
        raise LLMNotAllowedError("LLM extraction not enabled")

    logger.info("LLM extraction allowed for IP: %s", client_ip)


def _get_client_ip(request: Request) -> str | None:
    """Get the real client IP, checking X-Forwarded-For header for proxied requests."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return None
