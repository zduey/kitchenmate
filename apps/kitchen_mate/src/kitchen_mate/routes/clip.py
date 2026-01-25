"""Recipe clipping endpoint."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from recipe_clipper.exceptions import (
    LLMError,
    NetworkError,
    RecipeClipperError,
    RecipeNotFoundError,
    RecipeParsingError,
)
from recipe_clipper.models import Recipe

from kitchen_mate.auth import User, get_user
from kitchen_mate.config import Settings, get_settings
from kitchen_mate.database import get_cached_recipe, store_recipe, update_recipe
from kitchen_mate.extraction import LLMNotAllowedError, extract_recipe, get_client_ip
from kitchen_mate.files import FileValidationError, process_upload, save_to_temp_file
from kitchen_mate.schemas import ClipRequest, ClipResponse, ClipUploadResponse, FileInfo, Parser

logger = logging.getLogger(__name__)


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
            cached = await _get_from_cache(url, clip_request.force_llm)
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
            await _save_to_cache(url, recipe, content_hash, parsed_with)

        return ClipResponse(recipe=recipe, cached=False, content_changed=content_changed)

    except RecipeNotFoundError as error:
        raise HTTPException(
            status_code=404, detail="No recipe found at the requested url"
        ) from error
    except NetworkError as error:
        raise HTTPException(status_code=502, detail="Failed to fetch URL") from error
    except LLMNotAllowedError as error:
        raise HTTPException(
            status_code=403,
            detail="This reciple site requires advanced parsing. Upgrade to a paid account to parse this recipe.",
        ) from error
    except (RecipeParsingError, LLMError) as error:
        raise HTTPException(status_code=500, detail="Failed to parse recipe") from error
    except RecipeClipperError as error:
        raise HTTPException(status_code=500, detail="Failed to parse recipe") from error


async def _get_from_cache(url: str, force_llm: bool):
    """Try to get a recipe from cache."""
    if force_llm:
        return await get_cached_recipe(url, parsed_with=Parser.llm)
    return await get_cached_recipe(url)


async def _save_to_cache(url: str, recipe: Recipe, content_hash: str | None, parsed_with: Parser):
    """Save a recipe to cache."""
    existing = await get_cached_recipe(url)
    if existing:
        await update_recipe(url, recipe, content_hash, parsed_with)
    else:
        await store_recipe(url, recipe, content_hash, parsed_with)


@router.post("/clip/upload")
async def clip_recipe_from_upload(
    file: Annotated[UploadFile, File(description="Recipe image or document")],
    user: Annotated[User, Depends(get_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClipUploadResponse:
    """Extract a recipe from an uploaded file.

    This endpoint extracts the recipe but does NOT save it to the database.
    The extracted recipe is returned for user review/modification.
    Use POST /api/me/recipes with source_type='upload' to save after review.

    Supported formats:
    - Images: jpg, png, gif, webp (max 10MB)
    - Documents: pdf, docx, txt, md (max 20MB)

    This is a user-gated endpoint:
    - Single-tenant: Available to all (uses DEFAULT_USER)
    - Multi-tenant: Requires authentication
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="This feature only available for beta-testers.",
        )

    temp_path = None
    try:
        # Validate file (magic bytes + size)
        content, mime_type, ext, file_type = await process_upload(file)

        logger.info(
            "Processing %s upload: %s (%d bytes)",
            file_type,
            file.filename,
            len(content),
        )

        # Write to temp file for parsing
        temp_path = save_to_temp_file(content, ext)

        # Parse based on file type
        if file_type == "image":
            from recipe_clipper.parsers.llm_parser import parse_recipe_from_image

            recipe = await asyncio.to_thread(
                parse_recipe_from_image,
                temp_path,
                api_key=settings.anthropic_api_key,
            )
            parsing_method = Parser.llm_image
        else:
            from recipe_clipper.parsers.llm_parser import parse_recipe_from_document

            recipe = await asyncio.to_thread(
                parse_recipe_from_document,
                temp_path,
                api_key=settings.anthropic_api_key,
            )
            parsing_method = Parser.llm_document

        logger.info(
            "Successfully extracted recipe from %s: %s",
            file.filename,
            recipe.title,
        )

        return ClipUploadResponse(
            recipe=recipe,
            file_info=FileInfo(
                filename=file.filename or "unknown",
                file_type=file_type,
                file_size_bytes=len(content),
                content_type=mime_type,
            ),
            parsing_method=parsing_method.value,
        )

    except FileValidationError as e:
        logger.warning("File validation failed for %s: %s", file.filename, e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except LLMError as e:
        logger.error("LLM extraction failed for %s: %s", file.filename, e)
        raise HTTPException(
            status_code=422,
            detail=f"Failed to extract recipe from file: {e}",
        ) from e
    except RecipeClipperError as e:
        logger.error("Recipe extraction failed for %s: %s", file.filename, e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {e}",
        ) from e
    finally:
        # Always clean up temp file
        if temp_path and temp_path.exists():
            temp_path.unlink()
