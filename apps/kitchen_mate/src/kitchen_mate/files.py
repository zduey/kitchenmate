"""File upload handling with magic byte validation."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import UploadFile

# Magic byte signatures for supported formats
# Format: prefix bytes -> (mime_type, canonical_extension, file_type)
MAGIC_SIGNATURES: dict[bytes, tuple[str, str, str]] = {
    # Images
    b"\xff\xd8\xff": ("image/jpeg", ".jpg", "image"),
    b"\x89PNG\r\n\x1a\n": ("image/png", ".png", "image"),
    b"GIF87a": ("image/gif", ".gif", "image"),
    b"GIF89a": ("image/gif", ".gif", "image"),
    # Documents
    b"%PDF": ("application/pdf", ".pdf", "document"),
    b"PK\x03\x04": ("application/zip", ".docx", "document"),  # DOCX is a ZIP archive
}

# WEBP has a more complex signature: RIFF....WEBP
WEBP_SIGNATURE = (b"RIFF", b"WEBP")

# Text files don't have magic bytes - validate by extension + UTF-8 content
TEXT_EXTENSIONS = {".txt", ".md"}

# Valid extensions for each file type
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS

# Size limits (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB


class FileValidationError(Exception):
    """Raised when file validation fails."""

    pass


def detect_file_type(content: bytes, filename: str) -> tuple[str, str, str]:
    """Detect file type from magic bytes and validate against extension.

    Args:
        content: File content bytes (at least first 12 bytes needed)
        filename: Original filename for extension validation

    Returns:
        Tuple of (mime_type, extension, file_type) where file_type is 'image' or 'document'

    Raises:
        FileValidationError: If file type cannot be determined or doesn't match extension
    """
    ext = Path(filename).suffix.lower()

    if ext not in ALL_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file extension: {ext}. "
            f"Supported: {', '.join(sorted(ALL_EXTENSIONS))}"
        )

    # Handle text files (no magic bytes)
    if ext in TEXT_EXTENSIONS:
        try:
            content.decode("utf-8")
            mime = "text/markdown" if ext == ".md" else "text/plain"
            return mime, ext, "document"
        except UnicodeDecodeError as e:
            raise FileValidationError(
                f"File {filename} is not valid UTF-8 text"
            ) from e

    # Check for WEBP (special case: RIFF....WEBP format)
    if ext == ".webp":
        if content[:4] == WEBP_SIGNATURE[0] and WEBP_SIGNATURE[1] in content[:12]:
            return "image/webp", ".webp", "image"
        raise FileValidationError(
            "File content doesn't match .webp format (invalid WEBP signature)"
        )

    # Check magic bytes for other formats
    for magic, (mime, canonical_ext, file_type) in MAGIC_SIGNATURES.items():
        if content.startswith(magic):
            # Special case: DOCX - verify it's actually a DOCX not just any ZIP
            if magic == b"PK\x03\x04":
                if ext != ".docx":
                    # It's a ZIP but not named .docx
                    raise FileValidationError(
                        f"ZIP file detected but extension is {ext}, not .docx"
                    )
                # Check for word/ directory marker in ZIP
                if b"word/" not in content[:10000]:
                    raise FileValidationError(
                        "File appears to be a ZIP archive but not a valid DOCX"
                    )
                return mime, ext, file_type

            # Validate extension matches detected content
            valid_extensions = {canonical_ext}
            if canonical_ext == ".jpg":
                valid_extensions.add(".jpeg")

            if ext not in valid_extensions:
                raise FileValidationError(
                    f"File extension {ext} doesn't match detected content type {mime}. "
                    f"Expected extension: {canonical_ext}"
                )

            return mime, ext, file_type

    # No magic signature matched
    raise FileValidationError(
        f"Could not verify file content for {filename}. "
        f"File may be corrupted or not a supported format."
    )


def validate_file_size(content: bytes, file_type: str) -> None:
    """Validate file size against limits.

    Args:
        content: File content bytes
        file_type: 'image' or 'document'

    Raises:
        FileValidationError: If file exceeds size limit
    """
    max_size = MAX_IMAGE_SIZE if file_type == "image" else MAX_DOCUMENT_SIZE
    size = len(content)

    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        size_mb = size / (1024 * 1024)
        raise FileValidationError(
            f"File size ({size_mb:.1f}MB) exceeds {max_mb:.0f}MB limit for {file_type}s"
        )


async def process_upload(upload: "UploadFile") -> tuple[bytes, str, str, str]:
    """Process and validate an uploaded file.

    Args:
        upload: FastAPI UploadFile instance

    Returns:
        Tuple of (content, mime_type, extension, file_type)

    Raises:
        FileValidationError: If validation fails
    """
    if not upload.filename:
        raise FileValidationError("Filename is required")

    # Read content
    content = await upload.read()

    if len(content) == 0:
        raise FileValidationError("File is empty")

    # Detect and validate file type from magic bytes
    mime_type, ext, file_type = detect_file_type(content, upload.filename)

    # Validate size
    validate_file_size(content, file_type)

    return content, mime_type, ext, file_type


def save_to_temp_file(content: bytes, extension: str) -> Path:
    """Save content to a temporary file.

    Args:
        content: File content bytes
        extension: File extension (including dot)

    Returns:
        Path to temporary file (caller is responsible for cleanup)
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
        tmp.write(content)
        return Path(tmp.name)
