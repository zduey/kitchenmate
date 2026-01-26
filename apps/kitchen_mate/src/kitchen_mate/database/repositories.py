"""Async repository functions for database operations."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel
from sqlalchemy import select, update

from recipe_clipper.models import Recipe

from kitchen_mate.database.engine import get_session
from kitchen_mate.database.models import RecipeModel, UserRecipeModel
from kitchen_mate.schemas import Parser


# =============================================================================
# Pydantic schemas for database results
# =============================================================================


class CachedRecipe(BaseModel):
    """A cached recipe from the database (recipes table)."""

    id: str
    source_url: str
    source_domain: str
    recipe: Recipe
    content_hash: str | None
    parsing_method: str
    parsing_metadata: dict | None = None
    created_at: datetime
    updated_at: datetime


class UserRecipe(BaseModel):
    """A user's saved recipe from the database."""

    id: str
    user_id: str
    recipe_id: str
    recipe: Recipe
    is_modified: bool
    notes: str | None
    tags: list[str] | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class UserRecipeSummary(BaseModel):
    """Summary of a user's recipe for list views."""

    id: str
    source_url: str
    title: str
    image_url: str | None
    is_modified: bool
    tags: list[str] | None
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Helper functions
# =============================================================================


def _extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc


def hash_content(content: str) -> str:
    """Create a SHA-256 hash of content for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()


def _recipe_model_to_cached(model: RecipeModel) -> CachedRecipe:
    """Convert ORM model to Pydantic schema."""
    recipe_data = json.loads(model.recipe_data)
    parsing_metadata = json.loads(model.parsing_metadata) if model.parsing_metadata else None

    return CachedRecipe(
        id=model.id,
        source_url=model.source_url,
        source_domain=model.source_domain,
        recipe=Recipe.model_validate(recipe_data),
        content_hash=model.content_hash,
        parsing_method=model.parsing_method,
        parsing_metadata=parsing_metadata,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _user_recipe_model_to_schema(model: UserRecipeModel) -> UserRecipe:
    """Convert ORM model to Pydantic schema."""
    recipe_data = json.loads(model.recipe_data)
    tags_data = json.loads(model.tags) if model.tags else None

    return UserRecipe(
        id=model.id,
        user_id=model.user_id,
        recipe_id=model.recipe_id,
        recipe=Recipe.model_validate(recipe_data),
        is_modified=model.is_modified,
        notes=model.notes,
        tags=tags_data,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


# =============================================================================
# Cached Recipe Functions
# =============================================================================


async def get_cached_recipe(url: str, parsed_with: Parser | None = None) -> CachedRecipe | None:
    """Get a cached recipe by URL.

    Args:
        url: The recipe URL to look up
        parsed_with: If provided, only return if the recipe was parsed with this method

    Returns:
        CachedRecipe if found, None otherwise
    """
    async with get_session() as session:
        stmt = select(RecipeModel).where(RecipeModel.source_url == str(url))
        if parsed_with is not None:
            stmt = stmt.where(RecipeModel.parsing_method == parsed_with)

        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return _recipe_model_to_cached(row)


async def store_recipe(
    url: str, recipe: Recipe, content_hash: str | None, parsed_with: Parser
) -> CachedRecipe:
    """Store a recipe in the cache.

    Args:
        url: The recipe URL
        recipe: The extracted recipe
        content_hash: SHA-256 hash of the page content
        parsed_with: How the recipe was parsed ('recipe_scrapers' or 'llm')

    Returns:
        The cached recipe entry
    """
    recipe_id = str(uuid.uuid4())
    url_str = str(url)
    source_domain = _extract_domain(url_str)
    now = datetime.now()

    async with get_session() as session:
        model = RecipeModel(
            id=recipe_id,
            source_url=url_str,
            source_domain=source_domain,
            parsing_method=parsed_with,
            recipe_data=recipe.model_dump_json(),
            content_hash=content_hash,
            created_at=now,
            updated_at=now,
        )
        session.add(model)
        # Commit happens automatically via context manager

    return CachedRecipe(
        id=recipe_id,
        source_url=url_str,
        source_domain=source_domain,
        recipe=recipe,
        content_hash=content_hash,
        parsing_method=parsed_with,
        created_at=now,
        updated_at=now,
    )


async def update_recipe(
    url: str, recipe: Recipe, content_hash: str | None, parsed_with: Parser
) -> CachedRecipe:
    """Update an existing cached recipe.

    Args:
        url: The recipe URL
        recipe: The updated recipe
        content_hash: SHA-256 hash of the page content
        parsed_with: How the recipe was parsed ('recipe_scrapers' or 'llm')

    Returns:
        The updated cached recipe entry
    """
    url_str = str(url)
    now = datetime.now()

    async with get_session() as session:
        # Update the recipe
        stmt = (
            update(RecipeModel)
            .where(RecipeModel.source_url == url_str)
            .values(
                recipe_data=recipe.model_dump_json(),
                content_hash=content_hash,
                parsing_method=parsed_with,
                updated_at=now,
            )
        )
        await session.execute(stmt)

        # Fetch the updated record
        result = await session.execute(select(RecipeModel).where(RecipeModel.source_url == url_str))
        row = result.scalar_one_or_none()
        if row is None:
            raise RuntimeError(f"Failed to update recipe for URL: {url}")

        return CachedRecipe(
            id=row.id,
            source_url=row.source_url,
            source_domain=row.source_domain,
            recipe=recipe,
            content_hash=content_hash,
            parsing_method=parsed_with,
            created_at=row.created_at,
            updated_at=now,
        )


# =============================================================================
# User Recipe Functions
# =============================================================================


def _recipe_matches_search(
    recipe_data: dict, tags_data: list[str] | None, notes: str | None, search: str
) -> bool:
    """Check if a recipe matches the search query.

    Searches across title, ingredients, instructions, description, tags, and notes.
    """
    search_lower = search.lower()

    # Search in title
    title = recipe_data.get("title", "")
    if title and search_lower in title.lower():
        return True

    # Search in description
    description = recipe_data.get("description", "")
    if description and search_lower in description.lower():
        return True

    # Search in ingredients
    ingredients = recipe_data.get("ingredients", [])
    for ingredient in ingredients:
        if isinstance(ingredient, dict):
            text = ingredient.get("text", "")
        else:
            text = str(ingredient)
        if text and search_lower in text.lower():
            return True

    # Search in instructions
    instructions = recipe_data.get("instructions", [])
    for instruction in instructions:
        if isinstance(instruction, dict):
            text = instruction.get("text", "")
        else:
            text = str(instruction)
        if text and search_lower in text.lower():
            return True

    # Search in tags
    if tags_data:
        for tag in tags_data:
            if search_lower in tag.lower():
                return True

    # Search in notes
    if notes and search_lower in notes.lower():
        return True

    return False


async def get_user_recipes(
    user_id: str,
    cursor: str | None = None,
    limit: int = 50,
    tags: list[str] | None = None,
    modified_only: bool = False,
    search: str | None = None,
) -> tuple[list[UserRecipeSummary], str | None, bool]:
    """Get paginated user recipes.

    Args:
        user_id: The user's ID
        cursor: Cursor for pagination (recipe ID to start after)
        limit: Maximum number of recipes to return
        tags: Filter by tags (recipes must have ALL specified tags)
        modified_only: Only return modified recipes
        search: Free-text search across title, ingredients, instructions, tags, notes

    Returns:
        Tuple of (recipes, next_cursor, has_more)
    """
    async with get_session() as session:
        # Build base query with join
        stmt = (
            select(UserRecipeModel, RecipeModel.source_url)
            .join(RecipeModel, UserRecipeModel.recipe_id == RecipeModel.id)
            .where(UserRecipeModel.user_id == user_id)
            .where(UserRecipeModel.deleted_at.is_(None))
        )

        # Handle cursor-based pagination
        if cursor:
            cursor_stmt = select(UserRecipeModel.created_at).where(UserRecipeModel.id == cursor)
            cursor_result = await session.execute(cursor_stmt)
            cursor_row = cursor_result.scalar_one_or_none()
            if cursor_row:
                stmt = stmt.where(UserRecipeModel.created_at < cursor_row)

        if modified_only:
            stmt = stmt.where(UserRecipeModel.is_modified == True)  # noqa: E712

        stmt = stmt.order_by(UserRecipeModel.created_at.desc()).limit(limit + 1)

        result = await session.execute(stmt)
        rows = result.all()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        recipes = []
        for user_recipe, source_url in rows:
            recipe_data = json.loads(user_recipe.recipe_data)
            tags_data = json.loads(user_recipe.tags) if user_recipe.tags else None

            # Filter by tags in Python (same as current implementation)
            if tags and (not tags_data or not all(tag in tags_data for tag in tags)):
                continue

            # Filter by search query
            if search and not _recipe_matches_search(
                recipe_data, tags_data, user_recipe.notes, search
            ):
                continue

            recipes.append(
                UserRecipeSummary(
                    id=user_recipe.id,
                    source_url=source_url,
                    title=recipe_data.get("title", "Untitled"),
                    image_url=recipe_data.get("image"),
                    is_modified=user_recipe.is_modified,
                    tags=tags_data,
                    created_at=user_recipe.created_at,
                    updated_at=user_recipe.updated_at,
                )
            )

        next_cursor = rows[-1][0].id if rows and has_more else None
        return recipes, next_cursor, has_more


async def get_user_recipe(user_id: str, recipe_id: str) -> UserRecipe | None:
    """Get a specific user recipe by ID.

    Args:
        user_id: The user's ID
        recipe_id: The user recipe ID

    Returns:
        UserRecipe if found and belongs to user, None otherwise
    """
    async with get_session() as session:
        stmt = (
            select(UserRecipeModel)
            .where(UserRecipeModel.id == recipe_id)
            .where(UserRecipeModel.user_id == user_id)
            .where(UserRecipeModel.deleted_at.is_(None))
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        return _user_recipe_model_to_schema(row)


async def get_user_recipe_with_lineage(
    user_id: str, recipe_id: str
) -> tuple[UserRecipe, CachedRecipe] | None:
    """Get a user recipe along with its source recipe (lineage).

    Args:
        user_id: The user's ID
        recipe_id: The user recipe ID

    Returns:
        Tuple of (UserRecipe, CachedRecipe) if found, None otherwise
    """
    async with get_session() as session:
        stmt = (
            select(UserRecipeModel, RecipeModel)
            .join(RecipeModel, UserRecipeModel.recipe_id == RecipeModel.id)
            .where(UserRecipeModel.id == recipe_id)
            .where(UserRecipeModel.user_id == user_id)
            .where(UserRecipeModel.deleted_at.is_(None))
        )
        result = await session.execute(stmt)
        row = result.one_or_none()

        if row is None:
            return None

        user_recipe_model, recipe_model = row
        return _user_recipe_model_to_schema(user_recipe_model), _recipe_model_to_cached(
            recipe_model
        )


async def save_user_recipe(
    user_id: str,
    recipe_id: str,
    recipe_data: Recipe,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> tuple[UserRecipe, bool]:
    """Save a recipe to user's collection.

    If the user has already saved this recipe (even if soft-deleted), it will be restored.

    Args:
        user_id: The user's ID
        recipe_id: The source recipe ID (from recipes table)
        recipe_data: The recipe data to copy
        tags: Optional list of tags
        notes: Optional notes

    Returns:
        Tuple of (UserRecipe, is_new) - is_new is False if recipe was already saved or restored
    """
    user_recipe_id = str(uuid.uuid4())
    recipe_json = recipe_data.model_dump_json()
    tags_json = json.dumps(tags) if tags else None
    now = datetime.now()

    async with get_session() as session:
        # Check if user already has this recipe (including soft-deleted)
        stmt = select(UserRecipeModel).where(
            UserRecipeModel.user_id == user_id,
            UserRecipeModel.recipe_id == recipe_id,
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Recipe exists - restore if deleted, otherwise just return it
            if existing.deleted_at:
                # Restore soft-deleted recipe
                existing.deleted_at = None
                existing.updated_at = now
                if tags_json:
                    existing.tags = tags_json
                if notes:
                    existing.notes = notes
                # Commit happens via context manager

            # Return the existing recipe
            return _user_recipe_model_to_schema(existing), False

        # Insert new user recipe
        model = UserRecipeModel(
            id=user_recipe_id,
            user_id=user_id,
            recipe_id=recipe_id,
            recipe_data=recipe_json,
            is_modified=False,
            notes=notes,
            tags=tags_json,
            created_at=now,
            updated_at=now,
        )
        session.add(model)
        # Commit happens via context manager

    tags_list = tags if tags else None
    return (
        UserRecipe(
            id=user_recipe_id,
            user_id=user_id,
            recipe_id=recipe_id,
            recipe=recipe_data,
            is_modified=False,
            notes=notes,
            tags=tags_list,
            created_at=now,
            updated_at=now,
        ),
        True,
    )


async def update_user_recipe(
    user_id: str,
    recipe_id: str,
    recipe_data: Recipe | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> UserRecipe | None:
    """Update a user's recipe.

    Args:
        user_id: The user's ID
        recipe_id: The user recipe ID
        recipe_data: New recipe data (if modifying the recipe itself)
        tags: New tags (replaces existing)
        notes: New notes (replaces existing)

    Returns:
        Updated UserRecipe if found and belongs to user, None otherwise
    """
    now = datetime.now()

    async with get_session() as session:
        # Check if recipe exists and belongs to user
        stmt = (
            select(UserRecipeModel)
            .where(UserRecipeModel.id == recipe_id)
            .where(UserRecipeModel.user_id == user_id)
            .where(UserRecipeModel.deleted_at.is_(None))
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            return None

        # Update fields
        existing.updated_at = now

        if recipe_data is not None:
            existing.recipe_data = recipe_data.model_dump_json()
            existing.is_modified = True

        if tags is not None:
            existing.tags = json.dumps(tags) if tags else None

        if notes is not None:
            existing.notes = notes if notes else None

        # Commit happens via context manager
        return _user_recipe_model_to_schema(existing)


async def delete_user_recipe(user_id: str, recipe_id: str) -> bool:
    """Soft delete a user's recipe.

    Args:
        user_id: The user's ID
        recipe_id: The user recipe ID

    Returns:
        True if deleted, False if not found or not owned by user
    """
    now = datetime.now()

    async with get_session() as session:
        stmt = (
            update(UserRecipeModel)
            .where(UserRecipeModel.id == recipe_id)
            .where(UserRecipeModel.user_id == user_id)
            .where(UserRecipeModel.deleted_at.is_(None))
            .values(deleted_at=now, updated_at=now)
        )
        result = await session.execute(stmt)

        return result.rowcount > 0
