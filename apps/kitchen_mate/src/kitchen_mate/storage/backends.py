"""Storage backend implementations."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class StorageBackend(Protocol):
    """Protocol for storage backends."""

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        """Upload a file to storage."""
        ...

    def get_url(self, key: str) -> str:
        """Get the URL for a stored file."""
        ...

    async def delete(self, key: str) -> None:
        """Delete a stored file."""
        ...


class LocalStorageBackend:
    """Stores files on the local filesystem."""

    def __init__(self, base_path: Path, base_url: str) -> None:
        self._base_path = base_path
        self._base_url = base_url.rstrip("/")

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        file_path = self._resolve_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

    def get_url(self, key: str) -> str:
        return f"{self._base_url}/{key}"

    async def delete(self, key: str) -> None:
        file_path = self._resolve_path(key)
        if file_path.exists():
            file_path.unlink()

    def _resolve_path(self, key: str) -> Path:
        """Resolve a key to an absolute path, preventing path traversal."""
        base_resolved = self._base_path.resolve()
        resolved = (base_resolved / key).resolve()
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            raise ValueError(f"Invalid key: {key}")
        return resolved

    @property
    def base_path(self) -> Path:
        return self._base_path


class S3StorageBackend:
    """Stores files in an S3-compatible object store."""

    def __init__(
        self,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "us-east-1",
        endpoint_url: str | None = None,
        public_base_url: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._region = region
        self._endpoint_url = endpoint_url
        self._public_base_url = public_base_url.rstrip("/") if public_base_url else None

    def _get_client(self):  # type: ignore[return]
        import boto3  # type: ignore[import-untyped]

        return boto3.client(
            "s3",
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
            region_name=self._region,
            endpoint_url=self._endpoint_url,
        )

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        client = self._get_client()
        await asyncio.to_thread(
            client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    def get_url(self, key: str) -> str:
        if self._public_base_url:
            return f"{self._public_base_url}/{key}"
        # Generate presigned URL for private buckets
        client = self._get_client()
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=3600,
        )

    async def delete(self, key: str) -> None:
        client = self._get_client()
        await asyncio.to_thread(
            client.delete_object,
            Bucket=self._bucket,
            Key=key,
        )
