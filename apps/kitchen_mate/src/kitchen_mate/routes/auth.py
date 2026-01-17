"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from kitchen_mate.auth import User, get_current_user

router = APIRouter()


@router.get("/auth/me")
async def get_current_user_endpoint(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get the current authenticated user.

    Returns:
        User information from JWT token
    """
    return current_user
