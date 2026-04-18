"""Recipe sharing endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from kitchen_mate.auth import User, get_user
from kitchen_mate.database.repositories import (
    create_or_get_share,
    get_share_by_token,
    get_user_recipe_by_id_no_auth,
    revoke_share,
    save_user_recipe,
)
from kitchen_mate.schemas import CreateShareResponse, SaveSharedRecipeResponse, SharedRecipeResponse
from kitchen_mate.storage import StorageBackend, get_storage


router = APIRouter()


@router.post("/me/recipes/{recipe_id}/share", response_model=CreateShareResponse)
async def create_share(
    recipe_id: str,
    request: Request,
    user: Annotated[User, Depends(get_user)],
) -> CreateShareResponse:
    """Generate a shareable link for a recipe."""
    try:
        share = await create_or_get_share(user.id, recipe_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Recipe not found")

    base_url = f"{request.url.scheme}://{request.url.netloc}"
    share_url = f"{base_url}/shared/{share.share_token}"
    return CreateShareResponse(
        share_token=share.share_token,
        share_url=share_url,
        created_at=share.created_at.isoformat(),
        expires_at=share.expires_at.isoformat() if share.expires_at else None,
    )


@router.delete("/me/recipes/{recipe_id}/share", status_code=204)
async def delete_share(
    recipe_id: str,
    user: Annotated[User, Depends(get_user)],
) -> None:
    """Revoke a recipe's share link."""
    revoked = await revoke_share(user.id, recipe_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Share not found")


@router.get("/shared/{share_token}", response_model=SharedRecipeResponse)
async def get_shared_recipe(
    share_token: str,
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> SharedRecipeResponse:
    """View a shared recipe. No authentication required."""
    share = await get_share_by_token(share_token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    user_recipe = await get_user_recipe_by_id_no_auth(share.user_recipe_id)
    if user_recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    recipe = user_recipe.recipe
    if user_recipe.thumbnail_key:
        recipe = recipe.model_copy(update={"image": storage.get_url(user_recipe.thumbnail_key)})

    return SharedRecipeResponse(
        title=recipe.title,
        recipe=recipe,
        shared_at=share.created_at.isoformat(),
    )


@router.post("/shared/{share_token}/save", response_model=SaveSharedRecipeResponse)
async def save_shared_recipe(
    share_token: str,
    user: Annotated[User, Depends(get_user)],
) -> SaveSharedRecipeResponse:
    """Add a shared recipe to the authenticated user's collection."""
    share = await get_share_by_token(share_token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share link not found or expired")

    source = await get_user_recipe_by_id_no_auth(share.user_recipe_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    saved, is_new = await save_user_recipe(
        user_id=user.id,
        recipe_id=source.recipe_id,
        recipe_data=source.recipe,
    )
    return SaveSharedRecipeResponse(user_recipe_id=saved.id, is_new=is_new)
