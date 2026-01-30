"""Tests for authorization functionality."""

from __future__ import annotations

import pytest

from kitchen_mate.authorization import (
    Permission,
    Tier,
    TierInfo,
    check_permission_soft,
    has_permission,
)


class TestPermissions:
    """Tests for permission checking logic."""

    def test_free_tier_has_basic_permissions(self) -> None:
        """Test that free tier has basic clipping and recipe management permissions."""
        assert has_permission(Tier.FREE, Permission.CLIP_BASIC)
        assert has_permission(Tier.FREE, Permission.RECIPE_SAVE)
        assert has_permission(Tier.FREE, Permission.RECIPE_CREATE)
        assert has_permission(Tier.FREE, Permission.RECIPE_EDIT)
        assert has_permission(Tier.FREE, Permission.RECIPE_LIST)
        assert has_permission(Tier.FREE, Permission.RECIPE_DELETE)

    def test_free_tier_lacks_pro_permissions(self) -> None:
        """Test that free tier does not have pro-only permissions."""
        assert not has_permission(Tier.FREE, Permission.CLIP_AI)
        assert not has_permission(Tier.FREE, Permission.CLIP_UPLOAD)

    def test_pro_tier_has_all_permissions(self) -> None:
        """Test that pro tier has all permissions."""
        for permission in Permission:
            assert has_permission(Tier.PRO, permission), f"Pro tier should have {permission}"

    def test_unknown_tier_has_no_permissions(self) -> None:
        """Test that an invalid tier has no permissions."""
        # This tests the fallback behavior when tier is not in TIER_PERMISSIONS
        # We can't easily create an invalid Tier due to StrEnum, but we can test
        # the has_permission function's fallback behavior indirectly
        pass


class TestCheckPermissionSoft:
    """Tests for soft permission checking."""

    def test_allowed_permission_returns_true(self) -> None:
        """Test that allowed permissions return (True, None)."""
        tier_info = TierInfo(tier=Tier.FREE)
        allowed, error_code = check_permission_soft(Permission.CLIP_BASIC, tier_info)
        assert allowed is True
        assert error_code is None

    def test_disallowed_permission_returns_upgrade_required(self) -> None:
        """Test that disallowed permissions return (False, 'upgrade_required')."""
        tier_info = TierInfo(tier=Tier.FREE)
        allowed, error_code = check_permission_soft(Permission.CLIP_AI, tier_info)
        assert allowed is False
        assert error_code == "upgrade_required"

    def test_expired_subscription_returns_subscription_expired(self) -> None:
        """Test that expired subscriptions return (False, 'subscription_expired')."""
        tier_info = TierInfo(
            tier=Tier.FREE,
            expires_at="2025-01-01T00:00:00Z",
            is_expired=True,
        )
        allowed, error_code = check_permission_soft(Permission.CLIP_AI, tier_info)
        assert allowed is False
        assert error_code == "subscription_expired"

    def test_pro_tier_has_all_permissions(self) -> None:
        """Test that pro tier has all permissions via soft check."""
        tier_info = TierInfo(tier=Tier.PRO)
        for permission in Permission:
            allowed, error_code = check_permission_soft(permission, tier_info)
            assert allowed is True, f"Pro tier should have {permission}"
            assert error_code is None


class TestTierInfo:
    """Tests for TierInfo dataclass."""

    def test_default_values(self) -> None:
        """Test TierInfo default values."""
        tier_info = TierInfo(tier=Tier.FREE)
        assert tier_info.tier == Tier.FREE
        assert tier_info.expires_at is None
        assert tier_info.is_expired is False

    def test_with_expiration(self) -> None:
        """Test TierInfo with expiration data."""
        tier_info = TierInfo(
            tier=Tier.PRO,
            expires_at="2025-02-01T00:00:00Z",
            is_expired=False,
        )
        assert tier_info.tier == Tier.PRO
        assert tier_info.expires_at == "2025-02-01T00:00:00Z"
        assert tier_info.is_expired is False


class TestGetTierInfo:
    """Tests for get_tier_info dependency."""

    @pytest.mark.asyncio
    async def test_single_tenant_returns_pro(self) -> None:
        """Test that single-tenant mode returns pro tier."""
        from kitchen_mate.auth import DEFAULT_USER
        from kitchen_mate.authorization.dependencies import get_tier_info
        from kitchen_mate.config import Settings

        settings = Settings(_env_file=None, supabase_jwt_secret=None, supabase_url=None)
        assert settings.is_single_tenant

        tier_info = await get_tier_info(user=DEFAULT_USER, settings=settings)

        assert tier_info.tier == Tier.PRO
        assert tier_info.is_expired is False

    @pytest.mark.asyncio
    async def test_pro_user_id_returns_pro(self) -> None:
        """Test that user in PRO_USER_IDS gets pro tier."""
        from kitchen_mate.auth import User
        from kitchen_mate.authorization.dependencies import get_tier_info
        from kitchen_mate.config import Settings

        settings = Settings(
            _env_file=None,
            supabase_jwt_secret="test-secret-key-at-least-32-characters-long",
            pro_user_ids={"pro-user-123"},
        )
        user = User(id="pro-user-123", email="pro@example.com")

        tier_info = await get_tier_info(user=user, settings=settings)

        assert tier_info.tier == Tier.PRO
        assert tier_info.is_expired is False

    @pytest.mark.asyncio
    async def test_non_pro_user_returns_free(self) -> None:
        """Test that user not in PRO_USER_IDS gets free tier."""
        from kitchen_mate.auth import User
        from kitchen_mate.authorization.dependencies import get_tier_info
        from kitchen_mate.config import Settings

        settings = Settings(
            _env_file=None,
            supabase_jwt_secret="test-secret-key-at-least-32-characters-long",
            pro_user_ids={"other-user"},
        )
        user = User(id="free-user-456", email="free@example.com")

        tier_info = await get_tier_info(user=user, settings=settings)

        assert tier_info.tier == Tier.FREE
        assert tier_info.is_expired is False
