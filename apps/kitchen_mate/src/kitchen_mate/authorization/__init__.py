"""Authorization module for tier-based permissions."""

from __future__ import annotations

from kitchen_mate.authorization.dependencies import (
    TierInfo,
    check_permission_soft,
    get_tier_info,
    require_permission,
)
from kitchen_mate.authorization.exceptions import (
    SubscriptionExpiredError,
    UpgradeRequiredError,
)
from kitchen_mate.authorization.permissions import (
    Permission,
    Tier,
    TIER_PERMISSIONS,
    has_permission,
)

__all__ = [
    # Permissions
    "Permission",
    "Tier",
    "TIER_PERMISSIONS",
    "has_permission",
    # Dependencies
    "TierInfo",
    "get_tier_info",
    "require_permission",
    "check_permission_soft",
    # Exceptions
    "UpgradeRequiredError",
    "SubscriptionExpiredError",
]
