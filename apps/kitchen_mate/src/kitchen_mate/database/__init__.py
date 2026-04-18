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
from kitchen_mate.database.models import (
    Base,
    KitchenInviteModel,
    KitchenMemberModel,
    KitchenModel,
    KitchenRecipeModel,
    RecipeModel,
    RecipeShareModel,
    UserModel,
    UserRecipeModel,
)
from kitchen_mate.database.repositories import (
    CachedRecipe,
    DbUser,
    RecipeShare,
    UserRecipe,
    UserRecipeSummary,
    create_or_get_share,
    delete_user_recipe,
    get_cached_recipe,
    get_share_by_token,
    get_share_for_user_recipe,
    get_user_by_email,
    get_user_recipe,
    get_user_recipe_by_id_no_auth,
    get_user_recipe_with_lineage,
    get_user_recipes,
    hash_content,
    revoke_share,
    save_user_recipe,
    store_recipe,
    update_recipe,
    update_recipe_thumbnail_key,
    update_user_recipe,
    upsert_user,
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
    "UserModel",
    "RecipeShareModel",
    "KitchenModel",
    "KitchenMemberModel",
    "KitchenInviteModel",
    "KitchenRecipeModel",
    # Schemas
    "CachedRecipe",
    "UserRecipe",
    "UserRecipeSummary",
    "DbUser",
    "RecipeShare",
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
    "update_recipe_thumbnail_key",
    "delete_user_recipe",
    "upsert_user",
    "get_user_by_email",
    "create_or_get_share",
    "get_share_by_token",
    "get_share_for_user_recipe",
    "revoke_share",
    "get_user_recipe_by_id_no_auth",
]
