"""SQLite database operations for recipe caching."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator

from recipe_clipper.models import Recipe


@dataclass(frozen=True)
class CachedRecipe:
    """A cached recipe from the database."""

    id: str
    url: str
    recipe: Recipe
    content_hash: str | None
    parsed_with: str
    clipped_at: datetime
    updated_at: datetime


_db_path: str | None = None


def init_db(db_path: str) -> None:
    """Initialize the database, creating tables if they don't exist."""
    global _db_path
    _db_path = db_path

    # Create parent directory if needed
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clipped_recipes (
                id TEXT PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                url_hash TEXT NOT NULL,
                recipe_json TEXT NOT NULL,
                content_hash TEXT,
                parsed_with TEXT NOT NULL,
                clipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_url_hash ON clipped_recipes(url_hash)
        """)
        conn.commit()


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


def _hash_url(url: str) -> str:
    """Create a SHA-256 hash of a URL for indexing."""
    normalized = url.lower().strip().rstrip("/")
    return hashlib.sha256(normalized.encode()).hexdigest()


def hash_content(content: str) -> str:
    """Create a SHA-256 hash of content for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()


def get_cached_recipe(url: str, parsed_with: str | None = None) -> CachedRecipe | None:
    """Get a cached recipe by URL.

    Args:
        url: The recipe URL to look up
        parsed_with: If provided, only return if the recipe was parsed with this method
                     ('recipe_scrapers' or 'llm')

    Returns:
        CachedRecipe if found, None otherwise
    """
    url_hash = _hash_url(url)

    with _get_connection() as conn:
        if parsed_with is not None:
            cursor = conn.execute(
                """
                SELECT id, url, recipe_json, content_hash, parsed_with, clipped_at, updated_at
                FROM clipped_recipes
                WHERE url_hash = ? AND parsed_with = ?
                """,
                (url_hash, parsed_with),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, url, recipe_json, content_hash, parsed_with, clipped_at, updated_at
                FROM clipped_recipes
                WHERE url_hash = ?
                """,
                (url_hash,),
            )

        row = cursor.fetchone()
        if row is None:
            return None

        recipe_data = json.loads(row["recipe_json"])
        return CachedRecipe(
            id=row["id"],
            url=row["url"],
            recipe=Recipe.model_validate(recipe_data),
            content_hash=row["content_hash"],
            parsed_with=row["parsed_with"],
            clipped_at=datetime.fromisoformat(row["clipped_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )


def store_recipe(
    url: str, recipe: Recipe, content_hash: str | None, parsed_with: str
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
    url_hash = _hash_url(url)
    recipe_json = recipe.model_dump_json()
    now = datetime.now().isoformat()

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO clipped_recipes
            (id, url, url_hash, recipe_json, content_hash, parsed_with, clipped_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (recipe_id, url, url_hash, recipe_json, content_hash, parsed_with, now, now),
        )
        conn.commit()

    return CachedRecipe(
        id=recipe_id,
        url=url,
        recipe=recipe,
        content_hash=content_hash,
        parsed_with=parsed_with,
        clipped_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
    )


def update_recipe(
    url: str, recipe: Recipe, content_hash: str | None, parsed_with: str
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
    url_hash = _hash_url(url)
    recipe_json = recipe.model_dump_json()
    now = datetime.now().isoformat()

    with _get_connection() as conn:
        conn.execute(
            """
            UPDATE clipped_recipes
            SET recipe_json = ?, content_hash = ?, parsed_with = ?, updated_at = ?
            WHERE url_hash = ?
            """,
            (recipe_json, content_hash, parsed_with, now, url_hash),
        )
        conn.commit()

        # Fetch the updated record
        cursor = conn.execute(
            """
            SELECT id, url, clipped_at
            FROM clipped_recipes
            WHERE url_hash = ?
            """,
            (url_hash,),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"Failed to update recipe for URL: {url}")

    return CachedRecipe(
        id=row["id"],
        url=row["url"],
        recipe=recipe,
        content_hash=content_hash,
        parsed_with=parsed_with,
        clipped_at=datetime.fromisoformat(row["clipped_at"]),
        updated_at=datetime.fromisoformat(now),
    )
