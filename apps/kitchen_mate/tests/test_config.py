"""Tests for configuration module."""

from __future__ import annotations

from kitchen_mate.config import Settings


def test_pro_user_ids_from_string() -> None:
    """Test that pro_user_ids parses comma-separated string."""
    settings = Settings(pro_user_ids="user-1,user-2,user-3")
    assert settings.pro_user_ids == {"user-1", "user-2", "user-3"}


def test_pro_user_ids_from_string_with_spaces() -> None:
    """Test that spaces around user IDs are handled correctly."""
    settings = Settings(pro_user_ids=" user-1 , user-2 ")
    assert settings.pro_user_ids == {"user-1", "user-2"}


def test_pro_user_ids_from_string_with_empty_entries() -> None:
    """Test that empty entries are ignored."""
    settings = Settings(pro_user_ids="user-1,,user-2,")
    assert settings.pro_user_ids == {"user-1", "user-2"}


def test_pro_user_ids_empty_string() -> None:
    """Test that empty string results in empty set."""
    settings = Settings(pro_user_ids="")
    assert settings.pro_user_ids == set()


def test_pro_user_ids_none() -> None:
    """Test that None results in empty set."""
    settings = Settings(pro_user_ids=None)
    assert settings.pro_user_ids == set()


def test_pro_user_ids_already_set() -> None:
    """Test that a set is passed through unchanged."""
    settings = Settings(pro_user_ids={"user-1", "user-2"})
    assert settings.pro_user_ids == {"user-1", "user-2"}


def test_is_single_tenant_without_supabase() -> None:
    """Test single-tenant mode detection without Supabase config."""
    settings = Settings(supabase_jwt_secret=None, supabase_url=None)
    assert settings.is_single_tenant is True
    assert settings.is_multi_tenant is False


def test_is_multi_tenant_with_jwt_secret() -> None:
    """Test multi-tenant mode detection with JWT secret."""
    settings = Settings(
        supabase_jwt_secret="test-secret-key-at-least-32-characters-long",
        supabase_url=None,
    )
    assert settings.is_single_tenant is False
    assert settings.is_multi_tenant is True


def test_is_multi_tenant_with_supabase_url() -> None:
    """Test multi-tenant mode detection with Supabase URL."""
    settings = Settings(
        supabase_jwt_secret=None,
        supabase_url="https://example.supabase.co",
    )
    assert settings.is_single_tenant is False
    assert settings.is_multi_tenant is True
