"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to .env file relative to this config file (apps/kitchen_mate/.env)
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE, env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    anthropic_api_key: str | None = None
    default_timeout: int = 10

    # Pro user IDs (comma-separated in env var)
    pro_user_ids: set[str] = set()

    # Supabase authentication
    supabase_jwt_secret: str | None = None  # For HS256 verification (legacy)
    supabase_url: str | None = None  # For ES256 JWKS verification

    # CORS configuration
    cors_origins: str = "http://localhost:5173"

    # Database configuration
    cache_db_path: str = "kitchenmate.db"
    cache_enabled: bool = True

    @field_validator("pro_user_ids", mode="before")
    @classmethod
    def parse_pro_user_ids(cls, v: str | set[str] | None) -> set[str]:
        """Parse comma-separated user IDs from environment variable."""
        if v is None:
            return set()
        if isinstance(v, str):
            return {uid.strip() for uid in v.split(",") if uid.strip()}
        return v

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
