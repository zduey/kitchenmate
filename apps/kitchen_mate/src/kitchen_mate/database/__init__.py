"""Database module for kitchen_mate.

This module provides async database operations using SQLAlchemy ORM.
"""

from kitchen_mate.database.engine import (
    close_database,
    create_tables,
    get_engine,
    get_session,
    get_session_factory,
    init_database,
)
from kitchen_mate.database.models import Base, RecipeModel, UserRecipeModel
from kitchen_mate.database.repositories import (
    CachedRecipe,
    UserRecipe,
    UserRecipeSummary,
    delete_user_recipe,
    get_cached_recipe,
    get_user_recipe,
    get_user_recipe_with_lineage,
    get_user_recipes,
    hash_content,
    save_user_recipe,
    store_recipe,
    update_recipe,
    update_user_recipe,
)

__all__ = [
    # Engine management
    "init_database",
    "close_database",
    "create_tables",
    "get_engine",
    "get_session",
    "get_session_factory",
    # Models
    "Base",
    "RecipeModel",
    "UserRecipeModel",
    # Schemas
    "CachedRecipe",
    "UserRecipe",
    "UserRecipeSummary",
    # Repository functions
    "get_cached_recipe",
    "store_recipe",
    "update_recipe",
    "hash_content",
    "get_user_recipes",
    "get_user_recipe",
    "get_user_recipe_with_lineage",
    "save_user_recipe",
    "update_user_recipe",
    "delete_user_recipe",
]
