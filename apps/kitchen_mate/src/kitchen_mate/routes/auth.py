"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from kitchen_mate.auth import User, get_current_user
from kitchen_mate.authorization import TierInfo, get_tier_info
from kitchen_mate.config import Settings, get_settings
from kitchen_mate.database.kitchen_repositories import process_pending_invites
from kitchen_mate.database.repositories import upsert_user

router = APIRouter()


@router.get("/auth/me")
async def get_current_user_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    tier_info: Annotated[TierInfo, Depends(get_tier_info)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Get the current authenticated user with tier information."""
    if settings.is_multi_tenant and settings.database.enabled and current_user.email is not None:
        await upsert_user(current_user.id, current_user.email)
        try:
            await process_pending_invites(current_user.id, current_user.email)
        except Exception:
            pass  # Invite processing failures must not block auth

    return {
        "id": current_user.id,
        "email": current_user.email,
        "tier": tier_info.tier.value,
        "expires_at": tier_info.expires_at,
    }
