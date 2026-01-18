"""Application configuration using pydantic-settings."""

from __future__ import annotations

import ipaddress

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    anthropic_api_key: str | None = None
    default_timeout: int = 10
    llm_allowed_ips: str | None = None

    # Supabase authentication (only JWT secret needed for backend verification)
    supabase_jwt_secret: str | None = None

    # CORS configuration
    cors_origins: str = "http://localhost:5173"

    # Database configuration
    cache_db_path: str = "kitchenmate.db"
    cache_enabled: bool = True

    @property
    def is_multi_tenant(self) -> bool:
        """Check if running in multi-tenant mode (auth enabled)."""
        return self.supabase_jwt_secret is not None

    @property
    def is_single_tenant(self) -> bool:
        """Check if running in single-tenant mode (no auth)."""
        return self.supabase_jwt_secret is None


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


def is_ip_allowed(client_ip: str, allowed_ips: str | None) -> bool:
    """Check if a client IP is in the allowed list.

    Args:
        client_ip: The client's IP address
        allowed_ips: Comma-separated list of IPs or CIDR ranges, or None to block all

    Returns:
        True if the IP is allowed, False otherwise
    """
    if allowed_ips is None:
        return False

    try:
        client = ipaddress.ip_address(client_ip)
    except ValueError:
        return False

    for entry in allowed_ips.split(","):
        entry = entry.strip()
        if not entry:
            continue

        try:
            if "/" in entry:
                network = ipaddress.ip_network(entry, strict=False)
                if client in network:
                    return True
            else:
                if client == ipaddress.ip_address(entry):
                    return True
        except ValueError:
            continue

    return False
