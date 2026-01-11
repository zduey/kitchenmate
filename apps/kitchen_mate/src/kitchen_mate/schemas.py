"""Request and response schemas for the API."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class OutputFormat(str, Enum):
    """Supported output formats for recipe data."""

    text = "text"
    json = "json"
    markdown = "markdown"


class ClipRequest(BaseModel):
    """Request body for the /clip endpoint."""

    url: HttpUrl = Field(description="URL of the recipe page to extract")
    format: OutputFormat = Field(
        default=OutputFormat.json, description="Output format for the recipe data"
    )
    timeout: int = Field(default=10, ge=1, le=60, description="HTTP timeout in seconds")
    use_llm_fallback: bool = Field(
        default=False,
        description="Enable LLM fallback for unsupported sites (requires API key)",
    )
    download: bool = Field(default=False, description="Return response as a downloadable file")


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str = Field(description="Error message")
