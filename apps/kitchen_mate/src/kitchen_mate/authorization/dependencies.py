"""FastAPI dependencies for authorization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from kitchen_mate.auth import User, get_user
from kitchen_mate.authorization.exceptions import (
    SubscriptionExpiredError,
    UpgradeRequiredError,
)
from kitchen_mate.authorization.permissions import Permission, Tier, has_permission
from kitchen_mate.config import Settings, get_settings


@dataclass
class TierInfo:
    """User tier information including expiration status."""

    tier: Tier
    expires_at: str | None = None
    is_expired: bool = False


async def get_tier_info(
    user: Annotated[User, Depends(get_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TierInfo:
    """Determine user's tier.

    Priority:
    1. Single-tenant mode -> Pro
    2. User ID in PRO_USER_IDS -> Pro
    3. Default -> Free

    Args:
        user: The authenticated user
        settings: Application settings

    Returns:
        TierInfo with the user's tier and expiration status
    """
    if settings.is_single_tenant:
        return TierInfo(tier=Tier.PRO)

    if user.id in settings.pro_user_ids:
        return TierInfo(tier=Tier.PRO)

    return TierInfo(tier=Tier.FREE)


def require_permission(permission: Permission):
    """Dependency factory that ensures user has the required permission.

    Usage:
        @router.post("/clip/upload")
        async def clip_upload(
            user: User = Depends(require_permission(Permission.CLIP_UPLOAD)),
        ):
            ...

    Args:
        permission: The permission required to access the route

    Returns:
        A FastAPI dependency that returns the User if authorized
    """

    async def check_permission(
        tier_info: Annotated[TierInfo, Depends(get_tier_info)],
        user: Annotated[User, Depends(get_user)],
    ) -> User:
        if has_permission(tier_info.tier, permission):
            return user

        if tier_info.is_expired:
            raise SubscriptionExpiredError(
                feature=permission.value,
                expired_at=tier_info.expires_at or "",
            )

        raise UpgradeRequiredError(feature=permission.value)

    return check_permission


def check_permission_soft(
    permission: Permission,
    tier_info: TierInfo,
) -> tuple[bool, str | None]:
    """Check permission without raising. Returns (allowed, error_code).

    Args:
        permission: The permission to check
        tier_info: The user's tier information

    Returns:
        Tuple of (allowed, error_code).
        error_code is None if allowed, "upgrade_required" or "subscription_expired" otherwise.
    """
    if has_permission(tier_info.tier, permission):
        return True, None

    if tier_info.is_expired:
        return False, "subscription_expired"

    return False, "upgrade_required"
