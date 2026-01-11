"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str | None = None
    default_timeout: int = 10


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
