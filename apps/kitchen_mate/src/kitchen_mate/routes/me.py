"""User recipe management endpoints."""

from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from recipe_clipper.exceptions import (
    LLMError,
    NetworkError,
    RecipeClipperError,
    RecipeNotFoundError,
    RecipeParsingError,
)

from kitchen_mate.auth import User, get_user
from kitchen_mate.config import Settings, get_settings
from kitchen_mate.database import (
    delete_user_recipe,
    get_cached_recipe,
    get_user_recipe_with_lineage,
    get_user_recipes,
    save_user_recipe,
    store_recipe,
    update_user_recipe,
)
from kitchen_mate.extraction import LLMNotAllowedError, extract_recipe, get_client_ip
from kitchen_mate.schemas import (
    GetUserRecipeResponse,
    ListUserRecipesResponse,
    Parser,
    RecipeLineage,
    SaveRecipeRequest,
    SaveRecipeResponse,
    SourceType,
    UpdateUserRecipeRequest,
    UpdateUserRecipeResponse,
    UserRecipeSummaryResponse,
)


router = APIRouter()


@router.post("/me/recipes", status_code=201)
async def save_recipe(
    save_request: SaveRecipeRequest,
    request: Request,
    user: Annotated[User, Depends(get_user)],
    settings: Annotated[Settings, Depends(get_settings)],
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
        return await _save_web_recipe(save_request, request, user, settings)


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
    request: Request,
    user: User,
    settings: Settings,
) -> SaveRecipeResponse:
    """Save a recipe from a web URL."""
    url = str(save_request.url)
    client_ip = get_client_ip(request)

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
            api_key=settings.anthropic_api_key,
            client_ip=client_ip,
            allowed_ips=settings.llm_allowed_ips,
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
        raise HTTPException(status_code=403, detail=str(error)) from error
    except (RecipeParsingError, LLMError) as error:
        raise HTTPException(status_code=422, detail=f"Failed to parse recipe: {error}") from error
    except RecipeClipperError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/me/recipes")
async def list_recipes(
    user: Annotated[User, Depends(get_user)],
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
                image_url=r.image_url,
                is_modified=r.is_modified,
                tags=r.tags,
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
) -> GetUserRecipeResponse:
    """Get full details of a specific recipe from the user's collection."""
    result = await get_user_recipe_with_lineage(user.id, recipe_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    user_recipe, source_recipe = result

    return GetUserRecipeResponse(
        id=user_recipe.id,
        source_url=source_recipe.source_url,
        parsing_method=source_recipe.parsing_method,
        is_modified=user_recipe.is_modified,
        notes=user_recipe.notes,
        tags=user_recipe.tags,
        recipe=user_recipe.recipe,
        lineage=RecipeLineage(
            recipe_id=source_recipe.id,
            parsed_at=source_recipe.created_at.isoformat(),
        ),
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
