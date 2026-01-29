"""Shared recipe extraction logic for API endpoints."""

from __future__ import annotations

import asyncio
import logging

from recipe_clipper.exceptions import LLMError, RecipeParsingError
from recipe_clipper.http import fetch_url
from recipe_clipper.models import Recipe
from recipe_clipper.parsers.recipe_scrapers_parser import parse_with_recipe_scrapers

from kitchen_mate.database import get_cached_recipe, hash_content
from kitchen_mate.schemas import Parser


logger = logging.getLogger(__name__)


class LLMNotAllowedError(Exception):
    """Raised when LLM fallback is not allowed for the client."""

    pass


def check_llm_allowed(api_key: str | None, llm_permitted: bool) -> None:
    """Check if LLM usage is allowed for this request.

    Args:
        api_key: The Anthropic API key (None if not configured)
        llm_permitted: Whether the user has permission to use LLM

    Raises:
        LLMError: If no API key is configured
        LLMNotAllowedError: If the user does not have LLM permission
    """
    if not api_key:
        logger.warning("LLM extraction rejected: no API key configured")
        raise LLMError("LLM extraction requires ANTHROPIC_API_KEY environment variable")

    if not llm_permitted:
        logger.warning("LLM extraction rejected: user lacks permission")
        raise LLMNotAllowedError("LLM extraction not enabled")

    logger.info("LLM extraction allowed")


async def parse_with_llm(url: str, api_key: str | None) -> Recipe:
    """Parse a recipe using Claude LLM.

    Args:
        url: The URL to parse
        api_key: The Anthropic API key

    Returns:
        The extracted Recipe
    """
    from recipe_clipper.parsers.llm_parser import parse_with_claude

    return await asyncio.to_thread(parse_with_claude, url, api_key)


async def extract_recipe(
    url: str,
    timeout: int,
    use_llm_fallback: bool,
    api_key: str | None,
    llm_permitted: bool = False,
    force_llm: bool = False,
    check_content_changed: bool = False,
) -> tuple[Recipe, Parser, str | None, bool | None]:
    """Extract a recipe from a URL.

    This is the core extraction logic used by both /clip and /me/recipes endpoints.

    Args:
        url: The URL to extract from
        timeout: HTTP timeout in seconds
        use_llm_fallback: Whether to fall back to LLM if recipe-scrapers fails
        api_key: Anthropic API key for LLM extraction
        llm_permitted: Whether the user has permission to use LLM features
        force_llm: Skip recipe-scrapers and use LLM directly
        check_content_changed: If True, check if content changed vs cached version

    Returns:
        Tuple of (recipe, parsing_method, content_hash, content_changed)
        content_changed is None unless check_content_changed is True
    """
    if force_llm:
        check_llm_allowed(api_key, llm_permitted)
        recipe = await parse_with_llm(url, api_key)
        return recipe, Parser.llm, None, None

    # Fetch the page
    response = await asyncio.to_thread(fetch_url, url, timeout=timeout)
    content_hash = hash_content(response.content)

    # Check if content changed (for force_refresh scenarios)
    content_changed = None
    if check_content_changed:
        cached = await get_cached_recipe(url)
        if cached and cached.content_hash == content_hash:
            return cached.recipe, Parser(cached.parsing_method), content_hash, False
        content_changed = True

    # Try recipe_scrapers first
    try:
        recipe = await asyncio.to_thread(parse_with_recipe_scrapers, response)
        return recipe, Parser.recipe_scrapers, content_hash, content_changed
    except RecipeParsingError:
        if not use_llm_fallback:
            raise

    # Fall back to LLM
    check_llm_allowed(api_key, llm_permitted)
    recipe = await parse_with_llm(url, api_key)
    return recipe, Parser.llm, content_hash, content_changed
