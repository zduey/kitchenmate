"""User recipe management endpoints."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from recipe_clipper.exceptions import (
    LLMError,
    NetworkError,
    RecipeClipperError,
    RecipeNotFoundError,
    RecipeParsingError,
)
from recipe_clipper.models import Recipe

from kitchen_mate.auth import User, get_user
from kitchen_mate.authorization import (
    Permission,
    TierInfo,
    UpgradeRequiredError,
    check_permission_soft,
    get_tier_info,
    require_permission,
)
from kitchen_mate.config import Settings, get_settings
from kitchen_mate.database import (
    delete_user_recipe,
    get_cached_recipe,
    get_user_recipe,
    get_user_recipe_with_lineage,
    get_user_recipes,
    save_user_recipe,
    store_recipe,
    update_recipe_thumbnail_key,
    update_user_recipe,
)
from kitchen_mate.extraction import LLMNotAllowedError, extract_recipe
from kitchen_mate.files import FileValidationError, process_upload
from kitchen_mate.schemas import (
    GetUserRecipeResponse,
    ListUserRecipesResponse,
    Parser,
    RecipeLineage,
    SaveRecipeRequest,
    SaveRecipeResponse,
    SourceType,
    ThumbnailUploadResponse,
    UpdateUserRecipeRequest,
    UpdateUserRecipeResponse,
    UserRecipeSummaryResponse,
)
from kitchen_mate.storage import StorageBackend, get_storage

logger = logging.getLogger(__name__)


router = APIRouter()


def _resolve_image_url(
    recipe_image_url: str | None,
    thumbnail_key: str | None,
    storage: StorageBackend,
) -> str | None:
    """Return the best available image URL for a recipe."""
    if thumbnail_key:
        return storage.get_url(thumbnail_key)
    return recipe_image_url


@router.post("/me/recipes", status_code=201)
async def save_recipe(
    save_request: SaveRecipeRequest,
    user: Annotated[User, Depends(get_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    tier_info: Annotated[TierInfo, Depends(get_tier_info)],
) -> SaveRecipeResponse:
    """Save a recipe to the current user's collection.

    Supports two source types:
    - web: Provide URL, recipe will be fetched/parsed (or reused from cache)
    - upload: Provide recipe data directly (from /clip/upload preview)

    If the recipe has already been parsed/saved, it will be reused.
    If the user has already saved this recipe, the existing entry is returned.
    """
    if save_request.source_type in (SourceType.upload, SourceType.manual):
        return await _save_direct_recipe(save_request, user)
    else:
        return await _save_web_recipe(save_request, user, settings, tier_info)


async def _save_direct_recipe(
    save_request: SaveRecipeRequest,
    user: User,
) -> SaveRecipeResponse:
    """Save a recipe from upload or manual entry."""
    # Generate source identifier from recipe content hash
    recipe_json = save_request.recipe.model_dump_json()
    recipe_hash = hashlib.sha256(recipe_json.encode()).hexdigest()[:16]
    source_prefix = save_request.source_type.value
    source_url = f"{source_prefix}://{recipe_hash}"

    # Determine parsing method
    default_method = (
        "manual" if save_request.source_type == SourceType.manual else Parser.llm_image.value
    )
    parsing_method = save_request.parsing_method or default_method

    # Check if this exact recipe was already saved (by hash)
    cached = await get_cached_recipe(source_url)

    if cached:
        # Recipe already exists - just save to user's collection
        user_recipe, is_new = await save_user_recipe(
            user_id=user.id,
            recipe_id=cached.id,
            recipe_data=cached.recipe,
            tags=save_request.tags,
            notes=save_request.notes,
        )
        return SaveRecipeResponse(
            user_recipe_id=user_recipe.id,
            recipe_id=cached.id,
            source_url=cached.source_url,
            parsing_method=cached.parsing_method,
            created_at=user_recipe.created_at.isoformat(),
            is_new=is_new,
        )

    # Store the recipe
    cached = await store_recipe(
        url=source_url,
        recipe=save_request.recipe,
        content_hash=recipe_hash,
        parsed_with=Parser(parsing_method),
    )

    # Save to user's collection
    user_recipe, is_new = await save_user_recipe(
        user_id=user.id,
        recipe_id=cached.id,
        recipe_data=save_request.recipe,
        tags=save_request.tags,
        notes=save_request.notes,
    )

    return SaveRecipeResponse(
        user_recipe_id=user_recipe.id,
        recipe_id=cached.id,
        source_url=source_url,
        parsing_method=parsing_method,
        created_at=user_recipe.created_at.isoformat(),
        is_new=is_new,
    )


async def _save_web_recipe(
    save_request: SaveRecipeRequest,
    user: User,
    settings: Settings,
    tier_info: TierInfo,
) -> SaveRecipeResponse:
    """Save a recipe from a web URL."""
    url = str(save_request.url)

    # Check if user can use AI features
    # (authorization is only enforced if LLM fallback is actually needed)
    can_use_ai, _ = check_permission_soft(Permission.CLIP_AI, tier_info)

    try:
        # Check if recipe is already cached
        cached = await get_cached_recipe(url)

        if cached:
            # Recipe already exists - just save to user's collection
            user_recipe, is_new = await save_user_recipe(
                user_id=user.id,
                recipe_id=cached.id,
                recipe_data=cached.recipe,
                tags=save_request.tags,
                notes=save_request.notes,
            )
            return SaveRecipeResponse(
                user_recipe_id=user_recipe.id,
                recipe_id=cached.id,
                source_url=cached.source_url,
                parsing_method=cached.parsing_method,
                created_at=user_recipe.created_at.isoformat(),
                is_new=is_new,
            )

        # Recipe not cached - need to parse it
        recipe, parsed_with, content_hash, _ = await extract_recipe(
            url=url,
            timeout=save_request.timeout,
            use_llm_fallback=save_request.use_llm_fallback,
            api_key=settings.anthropic.api_key,
            llm_permitted=can_use_ai,
        )

        # Store the parsed recipe
        cached = await store_recipe(url, recipe, content_hash, parsed_with)

        # Save to user's collection
        user_recipe, is_new = await save_user_recipe(
            user_id=user.id,
            recipe_id=cached.id,
            recipe_data=recipe,
            tags=save_request.tags,
            notes=save_request.notes,
        )

        return SaveRecipeResponse(
            user_recipe_id=user_recipe.id,
            recipe_id=cached.id,
            source_url=cached.source_url,
            parsing_method=cached.parsing_method,
            created_at=user_recipe.created_at.isoformat(),
            is_new=is_new,
        )

    except RecipeNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except NetworkError as error:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {error}") from error
    except LLMNotAllowedError as error:
        raise UpgradeRequiredError(feature=Permission.CLIP_AI.value) from error
    except (RecipeParsingError, LLMError) as error:
        raise HTTPException(status_code=422, detail=f"Failed to parse recipe: {error}") from error
    except RecipeClipperError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/me/recipes/from-upload", status_code=201)
async def save_recipe_from_upload(
    file: Annotated[UploadFile, File(description="The uploaded recipe file")],
    recipe_json: Annotated[str, Form(description="Recipe JSON string")],
    parsing_method: Annotated[str, Form(description="Parsing method used")],
    user: Annotated[User, Depends(require_permission(Permission.CLIP_UPLOAD))],
    storage: Annotated[StorageBackend, Depends(get_storage)],
    tags_json: Annotated[str | None, Form(description="Tags JSON array")] = None,
    notes: Annotated[str | None, Form(description="Personal notes")] = None,
) -> SaveRecipeResponse:
    """Save a recipe that was extracted from an uploaded file.

    Atomically stores the file and saves the recipe in a single request.
    The file is only stored if the recipe save succeeds.
    """
    import json as _json

    try:
        recipe = Recipe.model_validate_json(recipe_json)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid recipe JSON: {exc}") from exc

    tags: list[str] | None = None
    if tags_json:
        try:
            tags = _json.loads(tags_json)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid tags JSON: {exc}") from exc

    try:
        content, mime_type, ext, file_type = await process_upload(file)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Build source identifier from recipe content
    recipe_json_str = recipe.model_dump_json()
    recipe_hash = hashlib.sha256(recipe_json_str.encode()).hexdigest()[:16]
    source_url = f"upload://{recipe_hash}"

    # Upsert the recipe into the cache table
    cached = await get_cached_recipe(source_url)
    if not cached:
        cached = await store_recipe(
            url=source_url,
            recipe=recipe,
            content_hash=recipe_hash,
            parsed_with=Parser(parsing_method),
        )

    # Build storage key using pre-generated user_recipe_id
    user_recipe_id = str(uuid.uuid4())
    safe_filename = f"source{ext}"
    storage_key = f"users/{user.id}/recipes/{user_recipe_id}/{safe_filename}"

    is_image = file_type == "image"
    thumbnail_key = storage_key if is_image else None

    # Upload file to storage first
    await storage.upload(storage_key, content, mime_type)

    try:
        user_recipe, is_new = await save_user_recipe(
            user_id=user.id,
            recipe_id=cached.id,
            recipe_data=recipe,
            tags=tags,
            notes=notes,
            user_recipe_id=user_recipe_id,
            source_file_key=storage_key,
            thumbnail_key=thumbnail_key,
        )
    except Exception:
        # Roll back the stored file if DB save fails
        try:
            await storage.delete(storage_key)
        except Exception:
            logger.warning("Failed to clean up storage key %s after DB error", storage_key)
        raise

    return SaveRecipeResponse(
        user_recipe_id=user_recipe.id,
        recipe_id=cached.id,
        source_url=source_url,
        parsing_method=parsing_method,
        created_at=user_recipe.created_at.isoformat(),
        is_new=is_new,
    )


@router.get("/me/recipes")
async def list_recipes(
    user: Annotated[User, Depends(get_user)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
    cursor: Annotated[str | None, Query(description="Cursor for pagination")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Number of recipes")] = 50,
    tags: Annotated[str | None, Query(description="Filter by tags (comma-separated)")] = None,
    modified_only: Annotated[bool, Query(description="Only show modified recipes")] = False,
    search: Annotated[str | None, Query(description="Free-text search query")] = None,
) -> ListUserRecipesResponse:
    """List all recipes in the current user's collection."""
    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    recipes, next_cursor, has_more = await get_user_recipes(
        user_id=user.id,
        cursor=cursor,
        limit=limit,
        tags=tag_list,
        modified_only=modified_only,
        search=search.strip() if search else None,
    )

    return ListUserRecipesResponse(
        recipes=[
            UserRecipeSummaryResponse(
                id=r.id,
                source_url=r.source_url,
                title=r.title,
                image_url=_resolve_image_url(r.image_url, r.thumbnail_key, storage),
                is_modified=r.is_modified,
                tags=r.tags,
                source_file_url=storage.get_url(r.source_file_key) if r.source_file_key else None,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
            )
            for r in recipes
        ],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/me/recipes/{recipe_id}")
async def get_recipe(
    recipe_id: str,
    user: Annotated[User, Depends(get_user)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> GetUserRecipeResponse:
    """Get full details of a specific recipe from the user's collection."""
    result = await get_user_recipe_with_lineage(user.id, recipe_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    user_recipe, source_recipe = result

    # Build recipe with resolved image URL if we have a stored thumbnail
    recipe = user_recipe.recipe
    if user_recipe.thumbnail_key:
        recipe = Recipe(
            **{**recipe.model_dump(), "image": storage.get_url(user_recipe.thumbnail_key)}
        )

    return GetUserRecipeResponse(
        id=user_recipe.id,
        source_url=source_recipe.source_url,
        parsing_method=source_recipe.parsing_method,
        is_modified=user_recipe.is_modified,
        notes=user_recipe.notes,
        tags=user_recipe.tags,
        recipe=recipe,
        lineage=RecipeLineage(
            recipe_id=source_recipe.id,
            parsed_at=source_recipe.created_at.isoformat(),
        ),
        source_file_url=storage.get_url(user_recipe.source_file_key)
        if user_recipe.source_file_key
        else None,
        created_at=user_recipe.created_at.isoformat(),
        updated_at=user_recipe.updated_at.isoformat(),
    )


@router.put("/me/recipes/{recipe_id}")
async def update_recipe_endpoint(
    recipe_id: str,
    update_request: UpdateUserRecipeRequest,
    user: Annotated[User, Depends(get_user)],
) -> UpdateUserRecipeResponse:
    """Update a recipe in the user's collection."""
    updated = await update_user_recipe(
        user_id=user.id,
        recipe_id=recipe_id,
        recipe_data=update_request.recipe,
        tags=update_request.tags,
        notes=update_request.notes,
    )

    if updated is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return UpdateUserRecipeResponse(
        id=updated.id,
        is_modified=updated.is_modified,
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/me/recipes/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: str,
    user: Annotated[User, Depends(get_user)],
) -> None:
    """Remove a recipe from the user's collection (soft delete)."""
    deleted = await delete_user_recipe(user.id, recipe_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Recipe not found")


@router.post("/me/recipes/{recipe_id}/thumbnail", status_code=200)
async def upload_recipe_thumbnail(
    recipe_id: str,
    file: Annotated[UploadFile, File(description="Thumbnail image")],
    user: Annotated[User, Depends(get_user)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> ThumbnailUploadResponse:
    """Upload or replace the thumbnail image for a saved recipe."""
    # Check recipe exists and belongs to user
    existing = await get_user_recipe(user.id, recipe_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    try:
        content, mime_type, ext, file_type = await process_upload(file)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if file_type != "image":
        raise HTTPException(status_code=400, detail="Only image files are accepted for thumbnails")

    new_key = f"users/{user.id}/recipes/{recipe_id}/thumbnail{ext}"
    old_key = existing.thumbnail_key

    await storage.upload(new_key, content, mime_type)

    updated = await update_recipe_thumbnail_key(recipe_id, user.id, new_key)
    if not updated:
        try:
            if old_key != new_key:
                await storage.delete(new_key)
        except Exception:
            pass
        raise HTTPException(status_code=404, detail="Recipe not found")

    if old_key and old_key != new_key:
        try:
            await storage.delete(old_key)
        except Exception:
            logger.warning("Failed to delete old thumbnail %s", old_key)

    return ThumbnailUploadResponse(image_url=storage.get_url(new_key))


@router.delete("/me/recipes/{recipe_id}/thumbnail", status_code=204)
async def delete_recipe_thumbnail(
    recipe_id: str,
    user: Annotated[User, Depends(get_user)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> None:
    """Remove the thumbnail for a saved recipe."""
    existing = await get_user_recipe(user.id, recipe_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if existing.thumbnail_key:
        try:
            await storage.delete(existing.thumbnail_key)
        except Exception:
            logger.warning("Failed to delete thumbnail %s", existing.thumbnail_key)

    await update_recipe_thumbnail_key(recipe_id, user.id, None)
