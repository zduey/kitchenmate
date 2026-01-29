"""Custom exceptions for authorization errors."""

from __future__ import annotations

from fastapi import HTTPException, status


class UpgradeRequiredError(HTTPException):
    """Raised when a free user attempts to use a pro feature."""

    def __init__(self, feature: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "This feature requires a Pro subscription.",
                "error_code": "upgrade_required",
                "required_tier": "pro",
                "feature": feature,
            },
        )


class SubscriptionExpiredError(HTTPException):
    """Raised when an expired pro user attempts to use a pro feature."""

    def __init__(self, feature: str, expired_at: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Your Pro subscription has expired.",
                "error_code": "subscription_expired",
                "required_tier": "pro",
                "feature": feature,
                "expired_at": expired_at,
            },
        )
