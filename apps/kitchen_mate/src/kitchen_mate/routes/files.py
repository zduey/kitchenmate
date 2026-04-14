"""Authenticated file serving route for local storage backend."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from kitchen_mate.auth import User, get_user
from kitchen_mate.storage import get_storage
from kitchen_mate.storage.backends import LocalStorageBackend, StorageBackend

router = APIRouter()


@router.get("/files/{file_key:path}")
async def serve_file(
    file_key: str,
    user: Annotated[User, Depends(get_user)],
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> FileResponse:
    """Serve a stored file for the authenticated user.

    Only serves files owned by the requesting user (key must start with users/{user.id}/).
    Only applicable for local storage backend; S3 backends redirect via URL.
    """
    if not isinstance(storage, LocalStorageBackend):
        raise HTTPException(status_code=404, detail="File not found")

    # Authorization: key must belong to this user
    expected_prefix = f"users/{user.id}/"
    if not file_key.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Access denied")

    # Resolve and validate the path (prevents traversal)
    try:
        base_resolved = storage.base_path.resolve()
        resolved = (base_resolved / file_key).resolve()
        resolved.relative_to(base_resolved)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file key")

    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=resolved)
