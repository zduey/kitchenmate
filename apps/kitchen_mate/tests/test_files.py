"""Tests for file validation module."""

from __future__ import annotations

import pytest

from kitchen_mate.files import (
    FileValidationError,
    detect_file_type,
    validate_file_size,
    MAX_IMAGE_SIZE,
    MAX_DOCUMENT_SIZE,
)


class TestDetectFileType:
    """Tests for detect_file_type function."""

    def test_jpeg_magic_bytes(self) -> None:
        """Test JPEG detection from magic bytes."""
        # JPEG files start with FF D8 FF
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
        mime, ext, file_type = detect_file_type(content, "photo.jpg")

        assert mime == "image/jpeg"
        assert ext == ".jpg"
        assert file_type == "image"

    def test_jpeg_with_jpeg_extension(self) -> None:
        """Test JPEG with .jpeg extension."""
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
        mime, ext, file_type = detect_file_type(content, "photo.jpeg")

        assert mime == "image/jpeg"
        assert ext == ".jpeg"
        assert file_type == "image"

    def test_png_magic_bytes(self) -> None:
        """Test PNG detection from magic bytes."""
        # PNG files start with 89 50 4E 47 0D 0A 1A 0A
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mime, ext, file_type = detect_file_type(content, "image.png")

        assert mime == "image/png"
        assert ext == ".png"
        assert file_type == "image"

    def test_gif87a_magic_bytes(self) -> None:
        """Test GIF87a detection from magic bytes."""
        content = b"GIF87a" + b"\x00" * 100
        mime, ext, file_type = detect_file_type(content, "animation.gif")

        assert mime == "image/gif"
        assert ext == ".gif"
        assert file_type == "image"

    def test_gif89a_magic_bytes(self) -> None:
        """Test GIF89a detection from magic bytes."""
        content = b"GIF89a" + b"\x00" * 100
        mime, ext, file_type = detect_file_type(content, "animation.gif")

        assert mime == "image/gif"
        assert ext == ".gif"
        assert file_type == "image"

    def test_webp_magic_bytes(self) -> None:
        """Test WEBP detection from magic bytes."""
        # WEBP files start with RIFF....WEBP
        content = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100
        mime, ext, file_type = detect_file_type(content, "photo.webp")

        assert mime == "image/webp"
        assert ext == ".webp"
        assert file_type == "image"

    def test_pdf_magic_bytes(self) -> None:
        """Test PDF detection from magic bytes."""
        content = b"%PDF-1.4" + b"\x00" * 100
        mime, ext, file_type = detect_file_type(content, "document.pdf")

        assert mime == "application/pdf"
        assert ext == ".pdf"
        assert file_type == "document"

    def test_docx_magic_bytes(self) -> None:
        """Test DOCX detection from magic bytes."""
        # DOCX is a ZIP file with word/ directory
        content = b"PK\x03\x04" + b"\x00" * 50 + b"word/" + b"\x00" * 100
        mime, ext, file_type = detect_file_type(content, "recipe.docx")

        assert mime == "application/zip"
        assert ext == ".docx"
        assert file_type == "document"

    def test_txt_file(self) -> None:
        """Test plain text file detection."""
        content = b"This is a recipe:\n\n1. Mix ingredients\n2. Bake"
        mime, ext, file_type = detect_file_type(content, "recipe.txt")

        assert mime == "text/plain"
        assert ext == ".txt"
        assert file_type == "document"

    def test_markdown_file(self) -> None:
        """Test markdown file detection."""
        content = b"# Recipe Title\n\n## Ingredients\n\n- Flour"
        mime, ext, file_type = detect_file_type(content, "recipe.md")

        assert mime == "text/markdown"
        assert ext == ".md"
        assert file_type == "document"

    def test_unsupported_extension(self) -> None:
        """Test that unsupported extensions are rejected."""
        content = b"some content"

        with pytest.raises(FileValidationError) as exc_info:
            detect_file_type(content, "file.xyz")

        assert "Unsupported file extension" in str(exc_info.value)
        assert ".xyz" in str(exc_info.value)

    def test_extension_content_mismatch(self) -> None:
        """Test that extension must match content type."""
        # PNG magic bytes but .jpg extension
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        with pytest.raises(FileValidationError) as exc_info:
            detect_file_type(content, "photo.jpg")

        assert "doesn't match" in str(exc_info.value)

    def test_invalid_webp_signature(self) -> None:
        """Test that invalid WEBP files are rejected."""
        # RIFF header but not WEBP
        content = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 100

        with pytest.raises(FileValidationError) as exc_info:
            detect_file_type(content, "audio.webp")

        assert "WEBP signature" in str(exc_info.value)

    def test_zip_not_docx(self) -> None:
        """Test that ZIP files without word/ directory are rejected as DOCX."""
        # ZIP file but not a DOCX (no word/ directory)
        content = b"PK\x03\x04" + b"\x00" * 200

        with pytest.raises(FileValidationError) as exc_info:
            detect_file_type(content, "archive.docx")

        assert "not a valid DOCX" in str(exc_info.value)

    def test_invalid_utf8_text(self) -> None:
        """Test that non-UTF8 content is rejected for text files."""
        # Invalid UTF-8 sequence
        content = b"\xff\xfe invalid utf8"

        with pytest.raises(FileValidationError) as exc_info:
            detect_file_type(content, "recipe.txt")

        assert "not valid UTF-8" in str(exc_info.value)

    def test_unknown_magic_bytes(self) -> None:
        """Test that files with unknown magic bytes are rejected."""
        content = b"\x00\x01\x02\x03" + b"\x00" * 100

        with pytest.raises(FileValidationError) as exc_info:
            detect_file_type(content, "unknown.jpg")

        assert "Could not verify file content" in str(exc_info.value)


class TestValidateFileSize:
    """Tests for validate_file_size function."""

    def test_image_within_limit(self) -> None:
        """Test that images within size limit pass."""
        content = b"\x00" * (MAX_IMAGE_SIZE - 1)
        # Should not raise
        validate_file_size(content, "image")

    def test_image_at_limit(self) -> None:
        """Test that images at exact size limit pass."""
        content = b"\x00" * MAX_IMAGE_SIZE
        # Should not raise
        validate_file_size(content, "image")

    def test_image_exceeds_limit(self) -> None:
        """Test that images exceeding size limit are rejected."""
        content = b"\x00" * (MAX_IMAGE_SIZE + 1)

        with pytest.raises(FileValidationError) as exc_info:
            validate_file_size(content, "image")

        assert "exceeds" in str(exc_info.value)
        assert "10" in str(exc_info.value)  # 10MB limit

    def test_document_within_limit(self) -> None:
        """Test that documents within size limit pass."""
        content = b"\x00" * (MAX_DOCUMENT_SIZE - 1)
        # Should not raise
        validate_file_size(content, "document")

    def test_document_exceeds_limit(self) -> None:
        """Test that documents exceeding size limit are rejected."""
        content = b"\x00" * (MAX_DOCUMENT_SIZE + 1)

        with pytest.raises(FileValidationError) as exc_info:
            validate_file_size(content, "document")

        assert "exceeds" in str(exc_info.value)
        assert "20" in str(exc_info.value)  # 20MB limit
