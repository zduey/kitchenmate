"""SQLite database operations for recipe caching and user recipe management."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator
from urllib.parse import urlparse

from pydantic import BaseModel

from recipe_clipper.models import Recipe
from kitchen_mate.schemas import Parser


_db_path: str | None = None

# Schema version for tracking migrations
SCHEMA_VERSION = 2


def init_db(db_path: str) -> None:
    """Initialize the database, creating tables if they don't exist."""
    global _db_path
    _db_path = db_path

    # Create parent directory if needed
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with _get_connection() as conn:
        # Check current schema version
        current_version = _get_schema_version(conn)

        if current_version == 0:
            # Fresh install or legacy schema - create/migrate to v2
            _migrate_to_v2(conn)
        elif current_version < SCHEMA_VERSION:
            # Future migrations would go here
            pass

        conn.commit()


def _get_schema_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version from the database."""
    # Check if schema_version table exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    )
    if cursor.fetchone() is None:
        # Check if old clipped_recipes table exists (legacy v1)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='clipped_recipes'"
        )
        if cursor.fetchone() is not None:
            return 1  # Legacy schema
        return 0  # Fresh install

    cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
    row = cursor.fetchone()
    return row[0] if row else 0


def _migrate_to_v2(conn: sqlite3.Connection) -> None:
    """Migrate from legacy schema (v1) or fresh install to v2."""
    # Create schema_version table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create new recipes table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id TEXT PRIMARY KEY,
            source_url TEXT UNIQUE NOT NULL,
            source_domain TEXT NOT NULL,
            parsing_method TEXT NOT NULL,
            recipe_data TEXT NOT NULL,
            content_hash TEXT,
            parsing_metadata TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for recipes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recipes_source_url ON recipes(source_url)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recipes_source_domain ON recipes(source_domain)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_recipes_parsing_method ON recipes(parsing_method)")

    # Create user_recipes table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_recipes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            recipe_id TEXT NOT NULL,
            recipe_data TEXT NOT NULL,
            is_modified INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            tags TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id),
            UNIQUE (user_id, recipe_id)
        )
    """)

    # Create indexes for user_recipes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_recipes_user_id ON user_recipes(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_recipes_recipe_id ON user_recipes(recipe_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_recipes_user_created ON user_recipes(user_id, created_at)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user_recipes_deleted ON user_recipes(deleted_at)")

    # Migrate data from legacy clipped_recipes if it exists
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='clipped_recipes'"
    )
    if cursor.fetchone() is not None:
        conn.execute("""
            INSERT OR IGNORE INTO recipes (id, source_url, source_domain, parsing_method, recipe_data, content_hash, created_at, updated_at)
            SELECT
                id,
                url,
                SUBSTR(url, INSTR(url, '://') + 3,
                       CASE WHEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') > 0
                            THEN INSTR(SUBSTR(url, INSTR(url, '://') + 3), '/') - 1
                            ELSE LENGTH(SUBSTR(url, INSTR(url, '://') + 3))
                       END),
                parsed_with,
                recipe_json,
                content_hash,
                clipped_at,
                updated_at
            FROM clipped_recipes
        """)
        # Keep the old table for now (can be dropped manually after verification)
        # conn.execute("DROP TABLE clipped_recipes")

    # Record migration
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))


@contextmanager
def _get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection with proper settings."""
    if _db_path is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


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


def get_cached_recipe(url: str, parsed_with: Parser | None = None) -> CachedRecipe | None:
    """Get a cached recipe by URL.

    Args:
        url: The recipe URL to look up
        parsed_with: If provided, only return if the recipe was parsed with this method
                     ('recipe_scrapers' or 'llm')

    Returns:
        CachedRecipe if found, None otherwise
    """
    with _get_connection() as conn:
        if parsed_with is not None:
            cursor = conn.execute(
                """
                SELECT id, source_url, source_domain, recipe_data, content_hash,
                       parsing_method, parsing_metadata, created_at, updated_at
                FROM recipes
                WHERE source_url = ? AND parsing_method = ?
                """,
                (str(url), parsed_with),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, source_url, source_domain, recipe_data, content_hash,
                       parsing_method, parsing_metadata, created_at, updated_at
                FROM recipes
                WHERE source_url = ?
                """,
                (str(url),),
            )

        row = cursor.fetchone()
        if row is None:
            return None

        recipe_data = json.loads(row["recipe_data"])
        parsing_metadata = json.loads(row["parsing_metadata"]) if row["parsing_metadata"] else None
        return CachedRecipe(
            id=row["id"],
            source_url=row["source_url"],
            source_domain=row["source_domain"],
            recipe=Recipe.model_validate(recipe_data),
            content_hash=row["content_hash"],
            parsing_method=row["parsing_method"],
            parsing_metadata=parsing_metadata,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


def store_recipe(
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
    recipe_json = recipe.model_dump_json()
    now = datetime.now().isoformat()

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO recipes
            (id, source_url, source_domain, parsing_method, recipe_data, content_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (recipe_id, url_str, source_domain, parsed_with, recipe_json, content_hash, now, now),
        )
        conn.commit()

    return CachedRecipe(
        id=recipe_id,
        source_url=url_str,
        source_domain=source_domain,
        recipe=recipe,
        content_hash=content_hash,
        parsing_method=parsed_with,
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
    )


def update_recipe(
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
    recipe_json = recipe.model_dump_json()
    now = datetime.now().isoformat()

    with _get_connection() as conn:
        conn.execute(
            """
            UPDATE recipes
            SET recipe_data = ?, content_hash = ?, parsing_method = ?, updated_at = ?
            WHERE source_url = ?
            """,
            (recipe_json, content_hash, parsed_with, now, url_str),
        )
        conn.commit()

        # Fetch the updated record
        cursor = conn.execute(
            """
            SELECT id, source_url, source_domain, created_at
            FROM recipes
            WHERE source_url = ?
            """,
            (url_str,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"Failed to update recipe for URL: {url}")

    return CachedRecipe(
        id=row["id"],
        source_url=row["source_url"],
        source_domain=row["source_domain"],
        recipe=recipe,
        content_hash=content_hash,
        parsing_method=parsed_with,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(now),
    )


def _extract_domain(url: str) -> str:
    """Extract the domain from a URL."""
    parsed = urlparse(url)
    return parsed.netloc


def hash_content(content: str) -> str:
    """Create a SHA-256 hash of content for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()


# =============================================================================
# User Recipe Functions
# =============================================================================


def get_user_recipes(
    user_id: str,
    cursor: str | None = None,
    limit: int = 50,
    tags: list[str] | None = None,
    modified_only: bool = False,
) -> tuple[list[UserRecipeSummary], str | None, bool]:
    """Get paginated user recipes.

    Args:
        user_id: The user's ID
        cursor: Cursor for pagination (recipe ID to start after)
        limit: Maximum number of recipes to return
        tags: Filter by tags (recipes must have ALL specified tags)
        modified_only: Only return modified recipes

    Returns:
        Tuple of (recipes, next_cursor, has_more)
    """
    with _get_connection() as conn:
        # Build query conditions
        conditions = ["ur.user_id = ?", "ur.deleted_at IS NULL"]
        params: list = [user_id]

        if cursor:
            # Get the created_at for the cursor recipe to paginate
            cursor_query = conn.execute(
                "SELECT created_at FROM user_recipes WHERE id = ?", (cursor,)
            )
            cursor_row = cursor_query.fetchone()
            if cursor_row:
                conditions.append("ur.created_at < ?")
                params.append(cursor_row["created_at"])

        if modified_only:
            conditions.append("ur.is_modified = 1")

        where_clause = " AND ".join(conditions)

        # Fetch one extra to check if there are more
        query = f"""
            SELECT ur.id, ur.recipe_data, ur.is_modified, ur.tags, ur.created_at, ur.updated_at,
                   r.source_url
            FROM user_recipes ur
            JOIN recipes r ON ur.recipe_id = r.id
            WHERE {where_clause}
            ORDER BY ur.created_at DESC
            LIMIT ?
        """
        params.append(limit + 1)

        cursor_result = conn.execute(query, params)
        rows = cursor_result.fetchall()

        # Check if there are more results
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        recipes = []
        for row in rows:
            recipe_data = json.loads(row["recipe_data"])
            tags_data = json.loads(row["tags"]) if row["tags"] else None

            # Filter by tags if specified
            if tags:
                if not tags_data or not all(tag in tags_data for tag in tags):
                    continue

            recipes.append(
                UserRecipeSummary(
                    id=row["id"],
                    source_url=row["source_url"],
                    title=recipe_data.get("title", "Untitled"),
                    image_url=recipe_data.get("image"),
                    is_modified=bool(row["is_modified"]),
                    tags=tags_data,
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            )

        next_cursor = rows[-1]["id"] if rows and has_more else None
        return recipes, next_cursor, has_more


def get_user_recipe(user_id: str, recipe_id: str) -> UserRecipe | None:
    """Get a specific user recipe by ID.

    Args:
        user_id: The user's ID
        recipe_id: The user recipe ID

    Returns:
        UserRecipe if found and belongs to user, None otherwise
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT ur.id, ur.user_id, ur.recipe_id, ur.recipe_data, ur.is_modified,
                   ur.notes, ur.tags, ur.created_at, ur.updated_at, ur.deleted_at
            FROM user_recipes ur
            WHERE ur.id = ? AND ur.user_id = ? AND ur.deleted_at IS NULL
            """,
            (recipe_id, user_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        recipe_data = json.loads(row["recipe_data"])
        tags_data = json.loads(row["tags"]) if row["tags"] else None

        return UserRecipe(
            id=row["id"],
            user_id=row["user_id"],
            recipe_id=row["recipe_id"],
            recipe=Recipe.model_validate(recipe_data),
            is_modified=bool(row["is_modified"]),
            notes=row["notes"],
            tags=tags_data,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
        )


def get_user_recipe_with_lineage(
    user_id: str, recipe_id: str
) -> tuple[UserRecipe, CachedRecipe] | None:
    """Get a user recipe along with its source recipe (lineage).

    Args:
        user_id: The user's ID
        recipe_id: The user recipe ID

    Returns:
        Tuple of (UserRecipe, CachedRecipe) if found, None otherwise
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT ur.id, ur.user_id, ur.recipe_id, ur.recipe_data, ur.is_modified,
                   ur.notes, ur.tags, ur.created_at, ur.updated_at, ur.deleted_at,
                   r.id as r_id, r.source_url, r.source_domain, r.recipe_data as r_recipe_data,
                   r.content_hash, r.parsing_method, r.parsing_metadata,
                   r.created_at as r_created_at, r.updated_at as r_updated_at
            FROM user_recipes ur
            JOIN recipes r ON ur.recipe_id = r.id
            WHERE ur.id = ? AND ur.user_id = ? AND ur.deleted_at IS NULL
            """,
            (recipe_id, user_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        user_recipe_data = json.loads(row["recipe_data"])
        tags_data = json.loads(row["tags"]) if row["tags"] else None
        source_recipe_data = json.loads(row["r_recipe_data"])
        parsing_metadata = json.loads(row["parsing_metadata"]) if row["parsing_metadata"] else None

        user_recipe = UserRecipe(
            id=row["id"],
            user_id=row["user_id"],
            recipe_id=row["recipe_id"],
            recipe=Recipe.model_validate(user_recipe_data),
            is_modified=bool(row["is_modified"]),
            notes=row["notes"],
            tags=tags_data,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
        )

        source_recipe = CachedRecipe(
            id=row["r_id"],
            source_url=row["source_url"],
            source_domain=row["source_domain"],
            recipe=Recipe.model_validate(source_recipe_data),
            content_hash=row["content_hash"],
            parsing_method=row["parsing_method"],
            parsing_metadata=parsing_metadata,
            created_at=datetime.fromisoformat(row["r_created_at"]),
            updated_at=datetime.fromisoformat(row["r_updated_at"]),
        )

        return user_recipe, source_recipe


def save_user_recipe(
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
    now = datetime.now().isoformat()

    with _get_connection() as conn:
        # Check if user already has this recipe (including soft-deleted)
        existing = conn.execute(
            """
            SELECT id, deleted_at FROM user_recipes
            WHERE user_id = ? AND recipe_id = ?
            """,
            (user_id, recipe_id),
        ).fetchone()

        if existing:
            # Recipe exists - restore if deleted, otherwise just return it
            if existing["deleted_at"]:
                # Restore soft-deleted recipe
                conn.execute(
                    """
                    UPDATE user_recipes
                    SET deleted_at = NULL, updated_at = ?, tags = COALESCE(?, tags), notes = COALESCE(?, notes)
                    WHERE id = ?
                    """,
                    (now, tags_json, notes, existing["id"]),
                )
                conn.commit()

            # Fetch and return the existing recipe
            user_recipe = get_user_recipe(user_id, existing["id"])
            return user_recipe, False

        # Insert new user recipe
        conn.execute(
            """
            INSERT INTO user_recipes
            (id, user_id, recipe_id, recipe_data, notes, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_recipe_id, user_id, recipe_id, recipe_json, notes, tags_json, now, now),
        )
        conn.commit()

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
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        ),
        True,
    )


def update_user_recipe(
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
    now = datetime.now().isoformat()

    with _get_connection() as conn:
        # Check if recipe exists and belongs to user
        existing = conn.execute(
            """
            SELECT id FROM user_recipes
            WHERE id = ? AND user_id = ? AND deleted_at IS NULL
            """,
            (recipe_id, user_id),
        ).fetchone()

        if not existing:
            return None

        # Build update query
        updates = ["updated_at = ?"]
        params: list = [now]

        if recipe_data is not None:
            updates.append("recipe_data = ?")
            updates.append("is_modified = 1")
            params.append(recipe_data.model_dump_json())

        if tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(tags) if tags else None)

        if notes is not None:
            updates.append("notes = ?")
            params.append(notes if notes else None)

        params.append(recipe_id)

        conn.execute(
            f"UPDATE user_recipes SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

    return get_user_recipe(user_id, recipe_id)


def delete_user_recipe(user_id: str, recipe_id: str) -> bool:
    """Soft delete a user's recipe.

    Args:
        user_id: The user's ID
        recipe_id: The user recipe ID

    Returns:
        True if deleted, False if not found or not owned by user
    """
    now = datetime.now().isoformat()

    with _get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE user_recipes
            SET deleted_at = ?, updated_at = ?
            WHERE id = ? AND user_id = ? AND deleted_at IS NULL
            """,
            (now, now, recipe_id, user_id),
        )
        conn.commit()

        return cursor.rowcount > 0
