"""Request and response schemas for the API."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, model_validator
from recipe_clipper.models import Recipe


class Parser(str, Enum):
    """Supported parsers"""

    recipe_scrapers = "recipe_scrapers"
    llm = "llm"
    llm_image = "llm_image"
    llm_document = "llm_document"
    manual = "manual"


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


class ClipResponse(BaseModel):
    """Response body for the /clip endpoint."""

    recipe: Recipe = Field(description="The extracted recipe")
    cached: bool = Field(default=False, description="Whether this was served from cache")
    content_changed: bool | None = Field(
        default=None,
        description="If force_refresh was used, whether the content changed since last clip",
    )


class FileInfo(BaseModel):
    """Information about an uploaded file."""

    filename: str = Field(description="Original filename")
    file_type: str = Field(description="Type: 'image' or 'document'")
    file_size_bytes: int = Field(description="File size in bytes")
    content_type: str = Field(description="MIME type")


class ClipUploadResponse(BaseModel):
    """Response body for extracting a recipe from an uploaded file."""

    recipe: Recipe = Field(description="The extracted recipe")
    file_info: FileInfo = Field(description="Upload file metadata")
    parsing_method: str = Field(description="Method used: 'llm_image' or 'llm_document'")


class ConvertRequest(BaseModel):
    """Request body for the /convert endpoint."""

    recipe: Recipe = Field(description="Recipe data to convert")
    format: OutputFormat = Field(description="Output format (text or markdown)")


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str = Field(description="Error message")


# =============================================================================
# User Recipe Schemas
# =============================================================================


class SourceType(str, Enum):
    """Source type for saved recipes."""

    web = "web"
    upload = "upload"
    manual = "manual"


class SaveRecipeRequest(BaseModel):
    """Request body for saving a recipe to user's collection.

    Supports two source types:
    - web: Provide URL, recipe will be fetched/parsed
    - upload: Provide recipe data directly (from /clip/upload preview)
    """

    # Web source fields
    url: HttpUrl | None = Field(
        default=None,
        description="URL of the recipe page to save (required for web source)",
    )
    timeout: int = Field(default=10, ge=1, le=60, description="HTTP timeout in seconds")
    use_llm_fallback: bool = Field(
        default=True,
        description="Enable LLM fallback for unsupported sites",
    )

    # Upload source fields
    source_type: SourceType = Field(
        default=SourceType.web,
        description="Source type: 'web' or 'upload'",
    )
    recipe: Recipe | None = Field(
        default=None,
        description="Recipe data (required for upload source)",
    )
    source_filename: str | None = Field(
        default=None,
        max_length=255,
        description="Original filename (for upload source)",
    )
    parsing_method: str | None = Field(
        default=None,
        description="Parsing method used (for upload source)",
    )

    # Common fields
    tags: list[str] | None = Field(
        default=None,
        max_length=20,
        description="Optional tags for organization (max 20)",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional personal notes (max 2000 chars)",
    )

    @model_validator(mode="after")
    def validate_source(self) -> "SaveRecipeRequest":
        """Validate that required fields are present based on source type."""
        if self.source_type == SourceType.web:
            if not self.url:
                raise ValueError("URL is required for web source")
        elif self.source_type in (SourceType.upload, SourceType.manual):
            if not self.recipe:
                raise ValueError("Recipe data is required for upload/manual source")
        return self


class SaveRecipeResponse(BaseModel):
    """Response body for saving a recipe."""

    user_recipe_id: str = Field(description="ID of the user's saved recipe")
    recipe_id: str = Field(description="ID of the source recipe")
    source_url: str = Field(description="Original recipe URL")
    parsing_method: str = Field(description="How the recipe was parsed")
    created_at: str = Field(description="When the recipe was saved")
    is_new: bool = Field(description="Whether this is a new save or already existed")


class UserRecipeSummaryResponse(BaseModel):
    """Summary of a user's recipe for list views."""

    id: str = Field(description="User recipe ID")
    source_url: str = Field(description="Original recipe URL")
    title: str = Field(description="Recipe title")
    image_url: str | None = Field(description="Recipe image URL")
    is_modified: bool = Field(description="Whether user has modified the recipe")
    tags: list[str] | None = Field(description="User-defined tags")
    source_file_url: str | None = Field(default=None, description="URL to the uploaded source file")
    created_at: str = Field(description="When saved to collection")
    updated_at: str = Field(description="Last modification time")


class ListUserRecipesResponse(BaseModel):
    """Response body for listing user recipes."""

    recipes: list[UserRecipeSummaryResponse] = Field(description="List of recipe summaries")
    next_cursor: str | None = Field(description="Cursor for next page, null if no more")
    has_more: bool = Field(description="Whether there are more recipes")


class RecipeLineage(BaseModel):
    """Lineage information for a user's recipe."""

    recipe_id: str = Field(description="Source recipe ID")
    parsed_at: str = Field(description="When the source was originally parsed")


class GetUserRecipeResponse(BaseModel):
    """Response body for getting a specific user recipe."""

    id: str = Field(description="User recipe ID")
    source_url: str = Field(description="Original recipe URL")
    parsing_method: str = Field(description="How the recipe was parsed")
    is_modified: bool = Field(description="Whether user has modified the recipe")
    notes: str | None = Field(description="User's personal notes")
    tags: list[str] | None = Field(description="User-defined tags")
    recipe: Recipe = Field(description="The recipe data")
    lineage: RecipeLineage = Field(description="Source recipe information")
    source_file_url: str | None = Field(default=None, description="URL to the uploaded source file")
    created_at: str = Field(description="When saved to collection")
    updated_at: str = Field(description="Last modification time")


class UpdateUserRecipeRequest(BaseModel):
    """Request body for updating a user recipe."""

    recipe: Recipe | None = Field(
        default=None,
        description="Modified recipe data (sets is_modified=true)",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Updated personal notes",
    )
    tags: list[str] | None = Field(
        default=None,
        max_length=20,
        description="Updated tags (replaces existing)",
    )


class UpdateUserRecipeResponse(BaseModel):
    """Response body for updating a user recipe."""

    id: str = Field(description="User recipe ID")
    is_modified: bool = Field(description="Whether the recipe has been modified")
    updated_at: str = Field(description="Last modification time")


class ThumbnailUploadResponse(BaseModel):
    """Response body for uploading a recipe thumbnail."""

    image_url: str = Field(description="URL to the uploaded thumbnail")


# =============================================================================
# Recipe Sharing Schemas
# =============================================================================


class CreateShareResponse(BaseModel):
    """Response body for creating a share link."""

    share_token: str = Field(description="Unique share token")
    share_url: str = Field(description="Full shareable URL")
    created_at: str = Field(description="When the share was created")
    expires_at: str | None = Field(description="Expiry time, null if no expiry")


class SharedRecipeResponse(BaseModel):
    """Public view of a shared recipe (no user-specific data)."""

    title: str = Field(description="Recipe title")
    recipe: Recipe = Field(description="The recipe data")
    shared_at: str = Field(description="When the share link was created")


class SaveSharedRecipeResponse(BaseModel):
    """Response body for saving a shared recipe to own collection."""

    user_recipe_id: str = Field(description="ID of the newly saved user recipe")
    is_new: bool = Field(description="Whether this is a new save or already existed")


# =============================================================================
# Kitchen Schemas
# =============================================================================


class CreateKitchenRequest(BaseModel):
    """Request body for creating a kitchen."""

    name: str = Field(min_length=1, max_length=100, description="Kitchen name")


class KitchenMemberResponse(BaseModel):
    """A member of a kitchen."""

    user_id: str = Field(description="User ID")
    email: str | None = Field(description="User email, if available")
    role: str = Field(description="Member role: 'admin' or 'member'")
    joined_at: str = Field(description="When the user joined the kitchen")


class KitchenSummaryResponse(BaseModel):
    """Summary of a kitchen for list views."""

    id: str = Field(description="Kitchen ID")
    name: str = Field(description="Kitchen name")
    created_by: str = Field(description="User ID of the creator")
    member_count: int = Field(description="Number of members")
    created_at: str = Field(description="When the kitchen was created")
    updated_at: str = Field(description="Last update time")


class KitchenDetailResponse(BaseModel):
    """Full detail of a kitchen including members."""

    id: str = Field(description="Kitchen ID")
    name: str = Field(description="Kitchen name")
    created_by: str = Field(description="User ID of the creator")
    members: list[KitchenMemberResponse] = Field(description="Kitchen members")
    created_at: str = Field(description="When the kitchen was created")
    updated_at: str = Field(description="Last update time")


class AddMemberRequest(BaseModel):
    """Request body for adding a member to a kitchen."""

    email: str = Field(description="Email address of the user to add")


class AddMemberResponse(BaseModel):
    """Response body for adding a member."""

    added: bool = Field(description="True if directly added, False if pending invite")
    message: str = Field(description="Human-readable status message")


class UpdateMemberRoleRequest(BaseModel):
    """Request body for updating a kitchen member's role."""

    role: str = Field(description="New role: 'admin' or 'member'")

    @model_validator(mode="after")
    def validate_role(self) -> "UpdateMemberRoleRequest":
        if self.role not in ("admin", "member"):
            raise ValueError("role must be 'admin' or 'member'")
        return self


class ShareToKitchenRequest(BaseModel):
    """Request body for sharing a recipe with a kitchen."""

    user_recipe_id: str = Field(description="ID of the user recipe to share")


class KitchenRecipeResponse(BaseModel):
    """A recipe shared with a kitchen."""

    id: str = Field(description="Kitchen recipe ID")
    kitchen_id: str = Field(description="Kitchen ID")
    user_recipe_id: str = Field(description="User recipe ID")
    shared_by: str = Field(description="User ID who shared the recipe")
    shared_at: str = Field(description="When the recipe was shared")
    title: str = Field(description="Recipe title")
    image_url: str | None = Field(description="Recipe image URL")
    tags: list[str] | None = Field(description="Tags from the original user recipe")


class ListKitchenRecipesResponse(BaseModel):
    """Response body for listing kitchen recipes."""

    recipes: list[KitchenRecipeResponse] = Field(description="List of kitchen recipes")
    next_cursor: str | None = Field(description="Cursor for next page")
    has_more: bool = Field(description="Whether there are more recipes")
