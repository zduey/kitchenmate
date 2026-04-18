"""Async repository functions for kitchen (group) operations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import func, select

from kitchen_mate.database.engine import get_session
from kitchen_mate.database.models import (
    KitchenInviteModel,
    KitchenMemberModel,
    KitchenModel,
    KitchenRecipeModel,
    UserModel,
    UserRecipeModel,
)
from kitchen_mate.database.repositories import get_user_by_email


# =============================================================================
# Pydantic schemas
# =============================================================================


class Kitchen(BaseModel):
    id: str
    name: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class KitchenMember(BaseModel):
    id: str
    kitchen_id: str
    user_id: str
    email: str | None
    role: str
    joined_at: datetime


class KitchenSummary(BaseModel):
    id: str
    name: str
    created_by: str
    member_count: int
    created_at: datetime
    updated_at: datetime


class KitchenDetail(BaseModel):
    id: str
    name: str
    created_by: str
    members: list[KitchenMember]
    created_at: datetime
    updated_at: datetime


class KitchenRecipe(BaseModel):
    id: str
    kitchen_id: str
    user_recipe_id: str
    shared_by: str
    shared_at: datetime
    title: str
    image_url: str | None
    tags: list[str] | None


# =============================================================================
# Helper functions
# =============================================================================


def _member_to_schema(model: KitchenMemberModel, email: str | None) -> KitchenMember:
    return KitchenMember(
        id=model.id,
        kitchen_id=model.kitchen_id,
        user_id=model.user_id,
        email=email,
        role=model.role,
        joined_at=model.joined_at,
    )


# =============================================================================
# Kitchen Functions
# =============================================================================


async def create_kitchen(user_id: str, name: str) -> KitchenSummary:
    """Create a new kitchen and add the creator as admin."""
    now = datetime.now()
    kitchen_id = str(uuid.uuid4())
    member_id = str(uuid.uuid4())

    async with get_session() as session:
        kitchen = KitchenModel(
            id=kitchen_id,
            name=name,
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        session.add(kitchen)

        member = KitchenMemberModel(
            id=member_id,
            kitchen_id=kitchen_id,
            user_id=user_id,
            role="admin",
            joined_at=now,
        )
        session.add(member)

    return KitchenSummary(
        id=kitchen_id,
        name=name,
        created_by=user_id,
        member_count=1,
        created_at=now,
        updated_at=now,
    )


async def get_user_kitchens(user_id: str) -> list[KitchenSummary]:
    """List all kitchens the user belongs to."""
    async with get_session() as session:
        stmt = (
            select(
                KitchenModel,
                func.count(KitchenMemberModel.id).label("member_count"),
            )
            .join(KitchenMemberModel, KitchenModel.id == KitchenMemberModel.kitchen_id)
            .where(
                KitchenModel.id.in_(
                    select(KitchenMemberModel.kitchen_id).where(
                        KitchenMemberModel.user_id == user_id
                    )
                )
            )
            .group_by(KitchenModel.id)
            .order_by(KitchenModel.created_at.desc())
        )
        result = await session.execute(stmt)
        rows = result.all()

        return [
            KitchenSummary(
                id=kitchen.id,
                name=kitchen.name,
                created_by=kitchen.created_by,
                member_count=count,
                created_at=kitchen.created_at,
                updated_at=kitchen.updated_at,
            )
            for kitchen, count in rows
        ]


async def get_kitchen(kitchen_id: str, user_id: str) -> KitchenDetail | None:
    """Get kitchen details. Returns None if the user is not a member."""
    async with get_session() as session:
        # Check membership
        membership_result = await session.execute(
            select(KitchenMemberModel)
            .where(KitchenMemberModel.kitchen_id == kitchen_id)
            .where(KitchenMemberModel.user_id == user_id)
        )
        if membership_result.scalar_one_or_none() is None:
            return None

        kitchen_result = await session.execute(
            select(KitchenModel).where(KitchenModel.id == kitchen_id)
        )
        kitchen = kitchen_result.scalar_one_or_none()
        if kitchen is None:
            return None

        # Fetch all members with email via LEFT JOIN on users table
        members_result = await session.execute(
            select(KitchenMemberModel, UserModel.email)
            .outerjoin(UserModel, KitchenMemberModel.user_id == UserModel.id)
            .where(KitchenMemberModel.kitchen_id == kitchen_id)
            .order_by(KitchenMemberModel.joined_at)
        )
        members = [_member_to_schema(member, email) for member, email in members_result.all()]

        return KitchenDetail(
            id=kitchen.id,
            name=kitchen.name,
            created_by=kitchen.created_by,
            members=members,
            created_at=kitchen.created_at,
            updated_at=kitchen.updated_at,
        )


async def get_member_role(kitchen_id: str, user_id: str) -> str | None:
    """Return the user's role in the kitchen, or None if not a member."""
    async with get_session() as session:
        result = await session.execute(
            select(KitchenMemberModel.role)
            .where(KitchenMemberModel.kitchen_id == kitchen_id)
            .where(KitchenMemberModel.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return row


async def add_or_invite_member(
    kitchen_id: str, invited_by_user_id: str, email: str
) -> tuple[KitchenMember | None, bool]:
    """Add a member directly if the email matches a known user, else create a pending invite.

    Returns:
        (KitchenMember, True) if directly added
        (None, False) if invite was created

    Raises:
        ValueError: If the user is already a member
    """
    existing_user = await get_user_by_email(email)

    async with get_session() as session:
        if existing_user is not None:
            # Check if already a member
            existing_member_result = await session.execute(
                select(KitchenMemberModel)
                .where(KitchenMemberModel.kitchen_id == kitchen_id)
                .where(KitchenMemberModel.user_id == existing_user.id)
            )
            if existing_member_result.scalar_one_or_none() is not None:
                raise ValueError(f"{email} is already a member of this kitchen")

            now = datetime.now()
            member_id = str(uuid.uuid4())
            member = KitchenMemberModel(
                id=member_id,
                kitchen_id=kitchen_id,
                user_id=existing_user.id,
                role="member",
                joined_at=now,
            )
            session.add(member)
            return (
                KitchenMember(
                    id=member_id,
                    kitchen_id=kitchen_id,
                    user_id=existing_user.id,
                    email=email,
                    role="member",
                    joined_at=now,
                ),
                True,
            )
        else:
            # Check if invite already exists
            existing_invite_result = await session.execute(
                select(KitchenInviteModel)
                .where(KitchenInviteModel.kitchen_id == kitchen_id)
                .where(KitchenInviteModel.invited_email == email)
            )
            if existing_invite_result.scalar_one_or_none() is not None:
                raise ValueError(f"Invite already sent to {email}")

            invite = KitchenInviteModel(
                id=str(uuid.uuid4()),
                kitchen_id=kitchen_id,
                invited_email=email,
                invited_by=invited_by_user_id,
                created_at=datetime.now(),
            )
            session.add(invite)
            return None, False


async def remove_member(kitchen_id: str, target_user_id: str) -> bool:
    """Remove a member from a kitchen. Returns False if not found."""
    async with get_session() as session:
        result = await session.execute(
            select(KitchenMemberModel)
            .where(KitchenMemberModel.kitchen_id == kitchen_id)
            .where(KitchenMemberModel.user_id == target_user_id)
        )
        member = result.scalar_one_or_none()
        if member is None:
            return False
        await session.delete(member)
        return True


async def process_pending_invites(user_id: str, email: str) -> int:
    """Resolve pending kitchen invites for an email address.

    Called on /auth/me to convert pending invites into actual memberships.
    Returns the number of kitchens joined.
    """
    async with get_session() as session:
        invites_result = await session.execute(
            select(KitchenInviteModel).where(KitchenInviteModel.invited_email == email)
        )
        invites = invites_result.scalars().all()

        if not invites:
            return 0

        now = datetime.now()
        count = 0
        for invite in invites:
            # Check not already a member (defensive)
            existing_result = await session.execute(
                select(KitchenMemberModel)
                .where(KitchenMemberModel.kitchen_id == invite.kitchen_id)
                .where(KitchenMemberModel.user_id == user_id)
            )
            if existing_result.scalar_one_or_none() is None:
                member = KitchenMemberModel(
                    id=str(uuid.uuid4()),
                    kitchen_id=invite.kitchen_id,
                    user_id=user_id,
                    role="member",
                    joined_at=now,
                )
                session.add(member)
                count += 1
            await session.delete(invite)

        return count


async def share_recipe_to_kitchen(
    kitchen_id: str, user_recipe_id: str, shared_by: str
) -> KitchenRecipe:
    """Share a user recipe with a kitchen.

    Raises:
        ValueError: If user is not a member, recipe not found/owned, or already shared
    """
    # Verify membership
    role = await get_member_role(kitchen_id, shared_by)
    if role is None:
        raise ValueError("Not a member of this kitchen")

    async with get_session() as session:
        # Verify recipe ownership
        recipe_result = await session.execute(
            select(UserRecipeModel)
            .where(UserRecipeModel.id == user_recipe_id)
            .where(UserRecipeModel.user_id == shared_by)
            .where(UserRecipeModel.deleted_at.is_(None))
        )
        user_recipe = recipe_result.scalar_one_or_none()
        if user_recipe is None:
            raise ValueError("Recipe not found or not owned by user")

        # Check if already shared
        existing_result = await session.execute(
            select(KitchenRecipeModel)
            .where(KitchenRecipeModel.kitchen_id == kitchen_id)
            .where(KitchenRecipeModel.user_recipe_id == user_recipe_id)
        )
        if existing_result.scalar_one_or_none() is not None:
            raise ValueError("Recipe is already shared with this kitchen")

        now = datetime.now()
        kr_id = str(uuid.uuid4())
        recipe_data = json.loads(user_recipe.recipe_data)
        tags_data = json.loads(user_recipe.tags) if user_recipe.tags else None

        model = KitchenRecipeModel(
            id=kr_id,
            kitchen_id=kitchen_id,
            user_recipe_id=user_recipe_id,
            shared_by=shared_by,
            shared_at=now,
        )
        session.add(model)

    return KitchenRecipe(
        id=kr_id,
        kitchen_id=kitchen_id,
        user_recipe_id=user_recipe_id,
        shared_by=shared_by,
        shared_at=now,
        title=recipe_data.get("title", "Untitled"),
        image_url=recipe_data.get("image"),
        tags=tags_data,
    )


async def get_kitchen_recipes(
    kitchen_id: str,
    user_id: str,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[list[KitchenRecipe], str | None, bool]:
    """List recipes shared with a kitchen. Returns None if user is not a member."""
    role = await get_member_role(kitchen_id, user_id)
    if role is None:
        raise ValueError("Not a member of this kitchen")

    async with get_session() as session:
        stmt = (
            select(KitchenRecipeModel, UserRecipeModel)
            .join(UserRecipeModel, KitchenRecipeModel.user_recipe_id == UserRecipeModel.id)
            .where(KitchenRecipeModel.kitchen_id == kitchen_id)
            .where(UserRecipeModel.deleted_at.is_(None))
        )

        if cursor:
            cursor_result = await session.execute(
                select(KitchenRecipeModel.shared_at).where(KitchenRecipeModel.id == cursor)
            )
            cursor_row = cursor_result.scalar_one_or_none()
            if cursor_row:
                stmt = stmt.where(KitchenRecipeModel.shared_at < cursor_row)

        stmt = stmt.order_by(KitchenRecipeModel.shared_at.desc()).limit(limit + 1)
        result = await session.execute(stmt)
        rows = result.all()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        recipes = []
        for kr, user_recipe in rows:
            recipe_data = json.loads(user_recipe.recipe_data)
            tags_data = json.loads(user_recipe.tags) if user_recipe.tags else None
            recipes.append(
                KitchenRecipe(
                    id=kr.id,
                    kitchen_id=kr.kitchen_id,
                    user_recipe_id=kr.user_recipe_id,
                    shared_by=kr.shared_by,
                    shared_at=kr.shared_at,
                    title=recipe_data.get("title", "Untitled"),
                    image_url=recipe_data.get("image"),
                    tags=tags_data,
                )
            )

        next_cursor = rows[-1][0].id if rows and has_more else None
        return recipes, next_cursor, has_more


async def remove_kitchen_recipe(kitchen_id: str, kitchen_recipe_id: str, user_id: str) -> bool:
    """Remove a recipe from a kitchen. Any member can remove."""
    role = await get_member_role(kitchen_id, user_id)
    if role is None:
        return False

    async with get_session() as session:
        result = await session.execute(
            select(KitchenRecipeModel)
            .where(KitchenRecipeModel.id == kitchen_recipe_id)
            .where(KitchenRecipeModel.kitchen_id == kitchen_id)
        )
        kr = result.scalar_one_or_none()
        if kr is None:
            return False
        await session.delete(kr)
        return True
