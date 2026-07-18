"""Kitchen (group) management endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from recipe_clipper.models import Recipe as RecipeData

from kitchen_mate.auth import User, get_user
from kitchen_mate.config import Settings, get_settings
from kitchen_mate.storage import StorageBackend, get_storage
from kitchen_mate.database.kitchen_repositories import (
    add_or_invite_member,
    create_kitchen,
    get_kitchen,
    get_kitchen_recipe_with_lineage,
    get_kitchen_recipes,
    get_member_role,
    get_user_kitchens,
    remove_kitchen_recipe,
    remove_member,
    share_recipe_to_kitchen,
    update_member_role,
)
from kitchen_mate.schemas import (
    AddMemberRequest,
    AddMemberResponse,
    CreateKitchenRequest,
    GetUserRecipeResponse,
    KitchenDetailResponse,
    KitchenMemberResponse,
    KitchenRecipeResponse,
    KitchenSummaryResponse,
    ListKitchenRecipesResponse,
    RecipeLineage,
    ShareToKitchenRequest,
    UpdateMemberRoleRequest,
)

router = APIRouter()


def _require_multi_tenant(settings: Annotated[Settings, Depends(get_settings)]) -> None:
    if settings.is_single_tenant:
        raise HTTPException(status_code=403, detail="Kitchens require multi-tenant mode")


async def _require_admin(kitchen_id: str, user: User) -> None:
    role = await get_member_role(kitchen_id, user.id)
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


async def _require_member(kitchen_id: str, user: User) -> None:
    role = await get_member_role(kitchen_id, user.id)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a kitchen member")


@router.post(
    "/kitchens",
    response_model=KitchenSummaryResponse,
    status_code=201,
    dependencies=[Depends(_require_multi_tenant)],
)
async def create_kitchen_endpoint(
    body: CreateKitchenRequest,
    user: Annotated[User, Depends(get_user)],
) -> KitchenSummaryResponse:
    """Create a new kitchen."""
    kitchen = await create_kitchen(user.id, body.name)
    return KitchenSummaryResponse(
        id=kitchen.id,
        name=kitchen.name,
        created_by=kitchen.created_by,
        member_count=kitchen.member_count,
        created_at=kitchen.created_at.isoformat(),
        updated_at=kitchen.updated_at.isoformat(),
    )


@router.get(
    "/kitchens",
    response_model=list[KitchenSummaryResponse],
    dependencies=[Depends(_require_multi_tenant)],
)
async def list_kitchens(
    user: Annotated[User, Depends(get_user)],
) -> list[KitchenSummaryResponse]:
    """List all kitchens the authenticated user belongs to."""
    kitchens = await get_user_kitchens(user.id)
    return [
        KitchenSummaryResponse(
            id=k.id,
            name=k.name,
            created_by=k.created_by,
            member_count=k.member_count,
            created_at=k.created_at.isoformat(),
            updated_at=k.updated_at.isoformat(),
        )
        for k in kitchens
    ]


@router.get(
    "/kitchens/{kitchen_id}",
    response_model=KitchenDetailResponse,
    dependencies=[Depends(_require_multi_tenant)],
)
async def get_kitchen_endpoint(
    kitchen_id: str,
    user: Annotated[User, Depends(get_user)],
) -> KitchenDetailResponse:
    """Get kitchen details including members."""
    kitchen = await get_kitchen(kitchen_id, user.id)
    if kitchen is None:
        raise HTTPException(status_code=404, detail="Kitchen not found or not a member")

    return KitchenDetailResponse(
        id=kitchen.id,
        name=kitchen.name,
        created_by=kitchen.created_by,
        members=[
            KitchenMemberResponse(
                user_id=m.user_id,
                email=m.email,
                role=m.role,
                joined_at=m.joined_at.isoformat(),
            )
            for m in kitchen.members
        ],
        created_at=kitchen.created_at.isoformat(),
        updated_at=kitchen.updated_at.isoformat(),
    )


@router.post(
    "/kitchens/{kitchen_id}/members",
    response_model=AddMemberResponse,
    dependencies=[Depends(_require_multi_tenant)],
)
async def add_member(
    kitchen_id: str,
    body: AddMemberRequest,
    user: Annotated[User, Depends(get_user)],
) -> AddMemberResponse:
    """Add a member to a kitchen (admin only). Sends pending invite if user not found."""
    await _require_admin(kitchen_id, user)

    try:
        member, directly_added = await add_or_invite_member(kitchen_id, user.id, body.email)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if directly_added:
        return AddMemberResponse(added=True, message=f"{body.email} added to the kitchen")
    return AddMemberResponse(
        added=False,
        message=f"Invite sent to {body.email}. They will be added when they sign in.",
    )


@router.delete(
    "/kitchens/{kitchen_id}/members/{target_user_id}",
    status_code=204,
    dependencies=[Depends(_require_multi_tenant)],
)
async def remove_member_endpoint(
    kitchen_id: str,
    target_user_id: str,
    user: Annotated[User, Depends(get_user)],
) -> None:
    """Remove a member from a kitchen (admin only)."""
    await _require_admin(kitchen_id, user)

    kitchen = await get_kitchen(kitchen_id, user.id)
    if kitchen is None:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    if target_user_id == kitchen.created_by:
        raise HTTPException(status_code=403, detail="Cannot remove the kitchen creator")

    removed = await remove_member(kitchen_id, target_user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found")


@router.patch(
    "/kitchens/{kitchen_id}/members/{target_user_id}",
    status_code=204,
    dependencies=[Depends(_require_multi_tenant)],
)
async def update_member_role_endpoint(
    kitchen_id: str,
    target_user_id: str,
    body: UpdateMemberRoleRequest,
    user: Annotated[User, Depends(get_user)],
) -> None:
    """Change a member's role (admin only). The kitchen creator's role cannot be changed."""
    await _require_admin(kitchen_id, user)

    kitchen = await get_kitchen(kitchen_id, user.id)
    if kitchen is None:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    if target_user_id == kitchen.created_by:
        raise HTTPException(status_code=403, detail="Cannot change the role of the kitchen creator")

    updated = await update_member_role(kitchen_id, target_user_id, body.role)
    if not updated:
        raise HTTPException(status_code=404, detail="Member not found")


@router.post(
    "/kitchens/{kitchen_id}/recipes",
    response_model=KitchenRecipeResponse,
    status_code=201,
    dependencies=[Depends(_require_multi_tenant)],
)
async def share_recipe(
    kitchen_id: str,
    body: ShareToKitchenRequest,
    user: Annotated[User, Depends(get_user)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> KitchenRecipeResponse:
    """Share a recipe with a kitchen (any member)."""
    await _require_member(kitchen_id, user)

    try:
        kr = await share_recipe_to_kitchen(kitchen_id, body.user_recipe_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    image_url = storage.get_url(kr.thumbnail_key) if kr.thumbnail_key else kr.image_url
    return KitchenRecipeResponse(
        id=kr.id,
        kitchen_id=kr.kitchen_id,
        user_recipe_id=kr.user_recipe_id,
        shared_by=kr.shared_by,
        shared_at=kr.shared_at.isoformat(),
        title=kr.title,
        image_url=image_url,
        tags=kr.tags,
    )


@router.get(
    "/kitchens/{kitchen_id}/recipes",
    response_model=ListKitchenRecipesResponse,
    dependencies=[Depends(_require_multi_tenant)],
)
async def list_kitchen_recipes(
    kitchen_id: str,
    user: Annotated[User, Depends(get_user)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
    cursor: str | None = None,
    limit: int = 50,
) -> ListKitchenRecipesResponse:
    """List recipes shared with a kitchen (any member)."""
    await _require_member(kitchen_id, user)

    try:
        recipes, next_cursor, has_more = await get_kitchen_recipes(
            kitchen_id, user.id, cursor, min(limit, 100)
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    return ListKitchenRecipesResponse(
        recipes=[
            KitchenRecipeResponse(
                id=r.id,
                kitchen_id=r.kitchen_id,
                user_recipe_id=r.user_recipe_id,
                shared_by=r.shared_by,
                shared_at=r.shared_at.isoformat(),
                title=r.title,
                image_url=storage.get_url(r.thumbnail_key) if r.thumbnail_key else r.image_url,
                tags=r.tags,
            )
            for r in recipes
        ],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/kitchens/{kitchen_id}/recipes/{kitchen_recipe_id}",
    response_model=GetUserRecipeResponse,
    dependencies=[Depends(_require_multi_tenant)],
)
async def get_kitchen_recipe(
    kitchen_id: str,
    kitchen_recipe_id: str,
    user: Annotated[User, Depends(get_user)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> GetUserRecipeResponse:
    """Get full details of a recipe shared with a kitchen (any member)."""
    await _require_member(kitchen_id, user)

    result = await get_kitchen_recipe_with_lineage(kitchen_id, kitchen_recipe_id, user.id)

    if result is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    user_recipe, source_recipe = result

    recipe = user_recipe.recipe
    if user_recipe.thumbnail_key:
        recipe = RecipeData(**{**recipe.model_dump(), "image": storage.get_url(user_recipe.thumbnail_key)})

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


@router.delete(
    "/kitchens/{kitchen_id}/recipes/{kitchen_recipe_id}",
    status_code=204,
    dependencies=[Depends(_require_multi_tenant)],
)
async def remove_recipe_from_kitchen(
    kitchen_id: str,
    kitchen_recipe_id: str,
    user: Annotated[User, Depends(get_user)],
) -> None:
    """Remove a recipe from a kitchen (any member)."""
    removed = await remove_kitchen_recipe(kitchen_id, kitchen_recipe_id, user.id)
    if not removed:
        raise HTTPException(status_code=404, detail="Recipe not found in kitchen")
