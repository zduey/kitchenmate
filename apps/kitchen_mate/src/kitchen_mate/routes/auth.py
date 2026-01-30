"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from kitchen_mate.auth import User, get_current_user
from kitchen_mate.authorization import TierInfo, get_tier_info

router = APIRouter()


@router.get("/auth/me")
async def get_current_user_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    tier_info: Annotated[TierInfo, Depends(get_tier_info)],
) -> dict:
    """Get the current authenticated user with tier information.

    Returns:
        User information from JWT token with tier
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "tier": tier_info.tier.value,
        "expires_at": tier_info.expires_at,
    }
