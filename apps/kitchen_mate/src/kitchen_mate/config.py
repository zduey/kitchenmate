"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to .env file relative to this config file (apps/kitchen_mate/.env)
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


def _parse_user_ids(value: str | set[str] | None) -> set[str]:
    """Parse comma-separated user IDs string into a set."""
    if value is None:
        return set()
    if isinstance(value, set):
        return value
    if not value:
        return set()
    return {uid.strip() for uid in value.split(",") if uid.strip()}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    anthropic_api_key: str | None = None
    default_timeout: int = 10

    # Pro user IDs - stored internally as string, exposed as set via property
    pro_user_ids_str: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PRO_USER_IDS", "pro_user_ids_str"),
    )

    # Supabase authentication
    supabase_jwt_secret: str | None = None  # For HS256 verification (legacy)
    supabase_url: str | None = None  # For ES256 JWKS verification

    # CORS configuration
    cors_origins: str = "http://localhost:5173"

    # Database configuration
    cache_db_path: str = "kitchenmate.db"
    cache_enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def handle_pro_user_ids(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Convert pro_user_ids to pro_user_ids_str if needed."""
        # Check for pro_user_ids in various forms
        pro_ids = data.pop("pro_user_ids", None) or data.pop("PRO_USER_IDS", None)
        if pro_ids is not None:
            if isinstance(pro_ids, set):
                data["pro_user_ids_str"] = ",".join(pro_ids)
            else:
                data["pro_user_ids_str"] = pro_ids
        return data

    @property
    def pro_user_ids(self) -> set[str]:
        """Get pro user IDs as a set."""
        return _parse_user_ids(self.pro_user_ids_str)

    @property
    def is_multi_tenant(self) -> bool:
        """Check if running in multi-tenant mode (auth enabled)."""
        return self.supabase_jwt_secret is not None or self.supabase_url is not None

    @property
    def is_single_tenant(self) -> bool:
        """Check if running in single-tenant mode (no auth)."""
        return not self.is_multi_tenant


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
