"""Storage backend factory and FastAPI dependency."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request

from kitchen_mate.config import Settings, get_settings
from kitchen_mate.storage.backends import LocalStorageBackend, S3StorageBackend, StorageBackend


def get_storage(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> StorageBackend:
    """FastAPI dependency that returns the configured storage backend.

    For local backend, the base_url is derived from the incoming request
    so it works behind proxies and in dev/prod without extra config.
    """
    if settings.storage_backend == "s3":
        return S3StorageBackend(
            bucket=settings.s3_bucket or "",
            access_key_id=settings.s3_access_key_id or "",
            secret_access_key=settings.s3_secret_access_key or "",
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            public_base_url=settings.storage_public_base_url,
        )

    # Local backend
    base_path = Path(settings.storage_local_path)
    if settings.storage_public_base_url:
        base_url = settings.storage_public_base_url
    else:
        # Build URL from request: scheme + host + /api/files
        base_url = f"{request.url.scheme}://{request.url.netloc}/api/files"
    return LocalStorageBackend(base_path=base_path, base_url=base_url)
