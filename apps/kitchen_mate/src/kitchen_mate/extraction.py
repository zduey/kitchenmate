"""Shared recipe extraction logic for API endpoints."""

from __future__ import annotations

import asyncio
import logging

from fastapi import Request

from recipe_clipper.exceptions import LLMError, RecipeParsingError
from recipe_clipper.http import fetch_url
from recipe_clipper.models import Recipe
from recipe_clipper.parsers.recipe_scrapers_parser import parse_with_recipe_scrapers

from kitchen_mate.config import is_ip_allowed
from kitchen_mate.db import get_cached_recipe, hash_content
from kitchen_mate.schemas import Parser


logger = logging.getLogger(__name__)


class LLMNotAllowedError(Exception):
    """Raised when LLM fallback is not allowed for the client."""

    pass


def get_client_ip(request: Request) -> str | None:
    """Get the real client IP, checking X-Forwarded-For header for proxied requests.

    Args:
        request: The FastAPI request object

    Returns:
        The client IP address or None if not available
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return None


def check_llm_allowed(client_ip: str | None, api_key: str | None, allowed_ips: str | None) -> None:
    """Check if LLM usage is allowed for this request.

    Args:
        client_ip: The client's IP address
        api_key: The Anthropic API key (None if not configured)
        allowed_ips: Comma-separated list of allowed IPs/CIDR ranges

    Raises:
        LLMError: If no API key is configured
        LLMNotAllowedError: If the client IP is not in the allowed list
    """
    logger.info("LLM extraction attempted from IP: %s", client_ip)

    if not api_key:
        logger.warning("LLM extraction rejected: no API key configured")
        raise LLMError("LLM extraction requires ANTHROPIC_API_KEY environment variable")

    if not client_ip or not is_ip_allowed(client_ip, allowed_ips):
        logger.warning("LLM extraction rejected: IP %s not in allowed list", client_ip)
        raise LLMNotAllowedError("LLM extraction not enabled")

    logger.info("LLM extraction allowed for IP: %s", client_ip)


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
    client_ip: str | None,
    allowed_ips: str | None,
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
        client_ip: Client IP for LLM access control
        allowed_ips: Allowed IPs for LLM access
        force_llm: Skip recipe-scrapers and use LLM directly
        check_content_changed: If True, check if content changed vs cached version

    Returns:
        Tuple of (recipe, parsing_method, content_hash, content_changed)
        content_changed is None unless check_content_changed is True
    """
    if force_llm:
        check_llm_allowed(client_ip, api_key, allowed_ips)
        recipe = await parse_with_llm(url, api_key)
        return recipe, Parser.llm, None, None

    # Fetch the page
    response = await asyncio.to_thread(fetch_url, url, timeout=timeout)
    content_hash = hash_content(response.content)

    # Check if content changed (for force_refresh scenarios)
    content_changed = None
    if check_content_changed:
        cached = get_cached_recipe(url)
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
    check_llm_allowed(client_ip, api_key, allowed_ips)
    recipe = await parse_with_llm(url, api_key)
    return recipe, Parser.llm, content_hash, content_changed
