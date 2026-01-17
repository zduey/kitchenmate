"""Request and response schemas for the API."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl
from recipe_clipper.models import Recipe


class OutputFormat(str, Enum):
    """Supported output formats for recipe data."""

    text = "text"
    json = "json"
    markdown = "markdown"
    pdf = "pdf"
    jpeg = "jpeg"
    png = "png"
    webp = "webp"
    svg = "svg"


class ClipRequest(BaseModel):
    """Request body for the /clip endpoint."""

    url: HttpUrl = Field(description="URL of the recipe page to extract")
    timeout: int = Field(default=10, ge=1, le=60, description="HTTP timeout in seconds")
    use_llm_fallback: bool = Field(
        default=True,
        description="Enable LLM fallback for unsupported sites (requires API key)",
    )
    force_llm: bool = Field(
        default=False,
        description="Skip recipe-scrapers and use LLM extraction directly",
    )
    force_refresh: bool = Field(
        default=False,
        description="Bypass cache and re-fetch the recipe, checking for content changes",
    )
    stream: bool = Field(
        default=False,
        description="Stream progress updates via Server-Sent Events",
    )


class ClipResponse(BaseModel):
    """Response body for the /clip endpoint."""

    recipe: Recipe = Field(description="The extracted recipe")
    cached: bool = Field(default=False, description="Whether this was served from cache")
    content_changed: bool | None = Field(
        default=None,
        description="If force_refresh was used, whether the content changed since last clip",
    )


class ConvertRequest(BaseModel):
    """Request body for the /convert endpoint."""

    recipe: Recipe = Field(description="Recipe data to convert")
    format: OutputFormat = Field(description="Output format (text or markdown)")


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str = Field(description="Error message")
