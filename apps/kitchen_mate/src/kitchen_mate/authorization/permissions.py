"""Permission and tier definitions for authorization."""

from __future__ import annotations

from enum import StrEnum


class Tier(StrEnum):
    """User subscription tiers."""

    FREE = "free"
    PRO = "pro"


class Permission(StrEnum):
    """Available permissions in the system."""

    CLIP_BASIC = "clip_basic"
    CLIP_AI = "clip_ai"
    CLIP_UPLOAD = "clip_upload"
    RECIPE_SAVE = "recipe_save"
    RECIPE_CREATE = "recipe_create"
    RECIPE_EDIT = "recipe_edit"
    RECIPE_LIST = "recipe_list"
    RECIPE_DELETE = "recipe_delete"


TIER_PERMISSIONS: dict[Tier, set[Permission]] = {
    Tier.FREE: {
        Permission.CLIP_BASIC,
        Permission.RECIPE_SAVE,
        Permission.RECIPE_CREATE,
        Permission.RECIPE_EDIT,
        Permission.RECIPE_LIST,
        Permission.RECIPE_DELETE,
    },
    Tier.PRO: {
        Permission.CLIP_BASIC,
        Permission.CLIP_AI,
        Permission.CLIP_UPLOAD,
        Permission.RECIPE_SAVE,
        Permission.RECIPE_CREATE,
        Permission.RECIPE_EDIT,
        Permission.RECIPE_LIST,
        Permission.RECIPE_DELETE,
    },
}


def has_permission(tier: Tier, permission: Permission) -> bool:
    """Check if a tier has a specific permission.

    Args:
        tier: The user's subscription tier
        permission: The permission to check

    Returns:
        True if the tier has the permission, False otherwise
    """
    return permission in TIER_PERMISSIONS.get(tier, set())
