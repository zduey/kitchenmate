# Design Document: Image & Document Recipe Clipping

## Overview

This feature extends Kitchen Mate's recipe extraction capabilities to support uploaded images and documents (PDF, DOCX, etc.) in addition to URLs. Users can extract recipes from:

- **Images**: Cookbook photos, recipe cards, handwritten notes, screenshots
- **Documents**: PDF cookbooks, Word documents, text files

This is a **user-gated feature** requiring authentication in multi-tenant mode, while remaining available in single-tenant deployments.

**Key capabilities**:
- Upload images or documents to extract recipes
- Persist uploaded files for re-parsing with improved models
- Download original uploaded files
- Re-extract recipes when parsing improvements are made

## Design Decisions

Based on requirements, this design implements:

### 1. Header Dropdown Navigation ✅

**Selected Approach**: Replace "Clip Recipe" with "Add Recipe" dropdown containing:
- **"From Web"**: URL-based recipe clipping (public access)
- **"From Upload"**: File upload (user-gated, grayed out until authenticated)

**Benefits**:
- Keeps header navigation clean
- Clear visual indication of auth requirement
- Maintains "My Recipes" tab structure
- Extensible for future input methods

### 2. File Persistence ✅

**Selected Approach**: Permanently store uploaded files in Supabase Storage

**Storage Strategy**:
- Primary: Supabase Storage (multi-tenant deployments)
- Fallback: Local filesystem (`./uploads/`) for single-tenant mode
- Structure: `{user_id}/{recipe_id}/original.{ext}`

**Database**: New `recipe_uploads` table with file metadata

**Enables**:
- Re-parsing with improved models
- Original file downloads
- Historical source tracking

### 3. User Gating ✅

**Selected Approach**: Upload feature requires authentication

**Implementation**:
- Backend: Use `get_user()` dependency (returns `DEFAULT_USER` in single-tenant)
- Frontend: Use `useRequireAuth()` hook to check authorization
- UI: "From Upload" option grayed out with lock icon when not signed in
- Behavior: Clicking when unauthorized shows sign-in modal

### 4. Re-parsing Functionality ✅

**Selected Approach**: Allow users to re-extract recipes from stored files

**Endpoint**: `POST /me/recipes/{id}/reparse`

**Use cases**:
- Model improvements (Claude upgrades)
- Parsing error corrections
- Better extraction accuracy over time

### 5. File Download ✅

**Selected Approach**: Users can download their original uploaded files

**Endpoint**: `GET /me/recipes/{id}/download`

**Implementation**: `StreamingResponse` with proper content-type and filename

## Existing Infrastructure

The library package already includes the necessary parsing functions:

- `parse_recipe_from_image()` in `packages/recipe_clipper/src/recipe_clipper/parsers/llm_parser.py:232`
- `parse_recipe_from_document()` in `packages/recipe_clipper/src/recipe_clipper/parsers/llm_parser.py:293`

These functions use Claude's vision and document APIs with structured outputs to extract recipe data.

### Supported Formats

**Images**:
- `.jpg`, `.jpeg` (image/jpeg)
- `.png` (image/png)
- `.gif` (image/gif)
- `.webp` (image/webp)

**Documents**:
- `.pdf` (application/pdf)
- `.docx` (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
- `.txt` (text/plain)
- `.md` (text/markdown)

## Architecture Design

### Backend Components

#### 1. File Upload Handling

Create a new module for file handling following the DRY principle:

**File**: `apps/kitchen_mate/src/kitchen_mate/files.py`

```python
"""File upload handling for recipe clipping."""

from pathlib import Path
from typing import BinaryIO
import hashlib
import tempfile

from fastapi import UploadFile
from recipe_clipper.parsers.llm_parser import (
    IMAGE_MEDIA_TYPES,
    DOCUMENT_MEDIA_TYPES,
)

# Maximum file sizes (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DOCUMENT_SIZE = 20 * 1024 * 1024  # 20 MB

ALLOWED_EXTENSIONS = set(IMAGE_MEDIA_TYPES.keys()) | set(DOCUMENT_MEDIA_TYPES.keys())


def validate_file_extension(filename: str) -> tuple[str, str]:
    """Validate file extension and return extension and file type.

    Returns:
        Tuple of (extension, file_type) where file_type is 'image' or 'document'

    Raises:
        ValueError: If extension is not supported
    """
    path = Path(filename)
    ext = path.suffix.lower()

    if ext in IMAGE_MEDIA_TYPES:
        return ext, "image"
    elif ext in DOCUMENT_MEDIA_TYPES:
        return ext, "document"
    else:
        raise ValueError(
            f"Unsupported file format: {ext}. "
            f"Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def validate_file_size(file: BinaryIO, max_size: int, file_type: str) -> None:
    """Validate file size.

    Raises:
        ValueError: If file exceeds max size
    """
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning

    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValueError(f"{file_type} size exceeds {max_mb}MB limit")


async def save_upload_to_temp(upload: UploadFile) -> Path:
    """Save uploaded file to temporary location.

    Args:
        upload: FastAPI UploadFile instance

    Returns:
        Path to temporary file

    Raises:
        ValueError: If file validation fails
    """
    # Validate extension
    ext, file_type = validate_file_extension(upload.filename or "")

    # Validate size
    max_size = MAX_IMAGE_SIZE if file_type == "image" else MAX_DOCUMENT_SIZE
    validate_file_size(upload.file, max_size, file_type.capitalize())

    # Create temp file with correct extension
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=ext,
        prefix=f"recipe_{file_type}_"
    )

    # Write uploaded content
    content = await upload.read()
    temp_file.write(content)
    temp_file.close()

    return Path(temp_file.name)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file for deduplication.

    Args:
        file_path: Path to file

    Returns:
        Hex digest of file hash
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()
```

#### 2. API Schemas

Update existing schemas in `apps/kitchen_mate/src/kitchen_mate/schemas.py`:

```python
# Update GetUserRecipeResponse to include upload information
class GetUserRecipeResponse(BaseModel):
    """Response body for getting a specific user recipe."""

    id: str
    source_url: str
    parsing_method: str
    is_modified: bool
    notes: str | None
    tags: list[str] | None
    recipe: Recipe
    lineage: RecipeLineage
    created_at: str
    updated_at: str

    # Upload information (null if not from upload)
    upload_info: UploadInfo | None = Field(
        default=None,
        description="File upload metadata if recipe was created from upload",
    )


class UploadInfo(BaseModel):
    """File upload metadata for recipes created from uploads."""

    file_type: str = Field(description="Type of file: 'image' or 'document'")
    original_filename: str = Field(description="Original uploaded filename")
    file_size_bytes: int = Field(description="File size in bytes")
    storage_url: str = Field(description="URL to download original file")
    can_reparse: bool = Field(description="Whether recipe can be re-parsed")


# Update UserRecipeSummaryResponse to indicate upload source
class UserRecipeSummaryResponse(BaseModel):
    """Summary of a user's recipe for list views."""

    id: str
    source_url: str
    title: str
    image_url: str | None
    is_modified: bool
    tags: list[str] | None
    created_at: str
    updated_at: str
    is_from_upload: bool = Field(
        default=False,
        description="Whether this recipe was created from a file upload",
    )
```

#### 3. Upload Route

Create new route: `apps/kitchen_mate/src/kitchen_mate/routes/upload.py`

```python
"""Recipe clipping from uploaded files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from recipe_clipper.exceptions import LLMError, RecipeClipperError
from recipe_clipper.parsers.llm_parser import (
    parse_recipe_from_image,
    parse_recipe_from_document,
)

from kitchen_mate.auth import User, get_user
from kitchen_mate.config import Settings, get_settings
from kitchen_mate.files import (
    save_upload_to_temp,
    compute_file_hash,
    validate_file_extension,
)
from kitchen_mate.schemas import ClipUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/me/recipes/upload", status_code=201)
async def upload_and_save_recipe(
    file: Annotated[UploadFile, File(description="Recipe image or document")],
    user: Annotated[User, Depends(get_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SaveRecipeResponse:
    """Extract recipe from uploaded file and save to user's collection.

    This is a user-gated endpoint:
    - Single-tenant: Available to all (uses DEFAULT_USER)
    - Multi-tenant: Requires authentication

    Workflow:
    1. Validate and save file to temp location
    2. Extract recipe using Claude API
    3. Generate recipe_id
    4. Upload file to permanent storage (Supabase or local)
    5. Save recipe to database (recipes + user_recipes tables)
    6. Save upload metadata (recipe_uploads table)
    7. Return saved recipe info

    Supported formats:
    - Images: jpg, png, gif, webp
    - Documents: pdf, docx, txt, md
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="Recipe extraction from uploads requires Anthropic API key",
        )

    temp_file = None
    try:
        # 1. Validate and save upload to temp
        temp_file = await save_upload_to_temp(file)
        ext, file_type = validate_file_extension(file.filename or "")
        file_hash = compute_file_hash(temp_file)

        # 2. Parse recipe based on file type
        if file_type == "image":
            recipe = parse_recipe_from_image(
                temp_file,
                api_key=settings.anthropic_api_key,
            )
        else:
            recipe = parse_recipe_from_document(
                temp_file,
                api_key=settings.anthropic_api_key,
            )

        # 3. Generate recipe ID
        recipe_id = str(uuid.uuid4())

        # 4. Upload file to permanent storage
        storage_path, storage_url = await upload_recipe_file(
            user_id=user.id,
            recipe_id=recipe_id,
            file_path=temp_file,
            original_filename=file.filename or "unknown",
            supabase_url=settings.supabase_storage_url,
            supabase_key=settings.supabase_service_role_key,
            bucket=settings.recipe_uploads_bucket,
        )

        # 5. Save to recipes table (use "upload" as source_url)
        source_url = f"upload://{user.id}/{recipe_id}"
        cached = await store_recipe(
            source_url=source_url,
            recipe=recipe,
            content_hash=file_hash,
            parsing_method=f"llm_{file_type}",
        )

        # 6. Save to user_recipes table
        user_recipe, is_new = await save_user_recipe(
            user_id=user.id,
            recipe_id=cached.id,
            recipe_data=recipe,
            tags=None,
            notes=None,
        )

        # 7. Save upload metadata
        await save_recipe_upload(
            recipe_id=cached.id,
            user_id=user.id,
            file_type=file_type,
            file_extension=ext,
            original_filename=file.filename or "unknown",
            file_size_bytes=temp_file.stat().st_size,
            storage_path=storage_path,
            storage_url=storage_url,
            file_hash=file_hash,
            mime_type=get_mime_type(ext),
        )

        logger.info(
            "Uploaded and saved recipe from %s for user %s: %s",
            file_type,
            user.id,
            recipe.title,
        )

        return SaveRecipeResponse(
            user_recipe_id=user_recipe.id,
            recipe_id=cached.id,
            source_url=source_url,
            parsing_method=f"llm_{file_type}",
            created_at=user_recipe.created_at.isoformat(),
            is_new=is_new,
        )

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except LLMError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract recipe: {error}",
        ) from error
    except RecipeClipperError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    finally:
        # Clean up temp file
        if temp_file and temp_file.exists():
            temp_file.unlink()
```

Register the route in `apps/kitchen_mate/src/kitchen_mate/main.py`:

```python
from kitchen_mate.routes import clip, convert, me, upload

app.include_router(upload.router, tags=["clip"])
```

### Frontend Components

#### 1. API Client

Add to `apps/kitchen_mate/frontend/src/api/recipes.ts`:

```typescript
export interface SaveRecipeResponse {
  user_recipe_id: string;
  recipe_id: string;
  source_url: string;
  parsing_method: string;
  created_at: string;
  is_new: boolean;
}

export interface UploadInfo {
  file_type: "image" | "document";
  original_filename: string;
  file_size_bytes: number;
  storage_url: string;
  can_reparse: boolean;
}

export async function uploadRecipe(
  file: File,
  onProgress?: (progress: number) => void
): Promise<SaveRecipeResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const xhr = new XMLHttpRequest();

  return new Promise((resolve, reject) => {
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress((e.loaded / e.total) * 100);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        const error = JSON.parse(xhr.responseText);
        reject(new Error(error.detail || "Failed to upload recipe"));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Network error during upload"));
    });

    xhr.open("POST", "/api/me/recipes/upload");
    xhr.withCredentials = true; // Include auth cookies
    xhr.send(formData);
  });
}

export async function reparseRecipe(recipeId: string): Promise<GetUserRecipeResponse> {
  const response = await fetch(`/api/me/recipes/${recipeId}/reparse`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to reparse recipe");
  }

  return response.json();
}
```

#### 2. UI Design: Header Dropdown Navigation

**Selected Approach**: Dropdown menu in header navigation

Update the header navigation to replace "Clip Recipe" with "Add Recipe" dropdown:

```
Header:
┌────────────────────────────────────────────────────────────┐
│  🔖 Recipleased   [Add Recipe ▼]  [My Recipes]  [Sign In] │
└────────────────────────────────────────────────────────────┘

When "Add Recipe" is clicked:
┌────────────────────┐
│  From Web          │  ← URL-based clipping (public)
│  From Upload       │  ← File upload (requires auth, grayed if not signed in)
└────────────────────┘
```

**Navigation Flow**:

1. **Unauthenticated users**:
   - "Add Recipe" dropdown shows both options
   - "From Web" is enabled (navigates to URL input page)
   - "From Upload" is **grayed out** with tooltip: "Sign in to upload recipes"
   - Clicking "From Upload" shows sign-in modal

2. **Authenticated users**:
   - Both "From Web" and "From Upload" are enabled
   - "From Upload" navigates to file upload interface
   - Both routes save to user's collection

**Header Component Changes** (`Header.tsx`):

Replace the single "Clip Recipe" link with a dropdown menu component:

```typescript
<DropdownMenu>
  <DropdownMenu.Trigger>
    Add Recipe <ChevronDownIcon />
  </DropdownMenu.Trigger>

  <DropdownMenu.Content>
    <DropdownMenu.Item asChild>
      <Link to="/clip">From Web</Link>
    </DropdownMenu.Item>

    <DropdownMenu.Item
      disabled={!isAuthorized}
      onClick={() => !isAuthorized && setShowSignInModal(true)}
    >
      <Link to="/upload" className={!isAuthorized ? "text-gray-400" : ""}>
        From Upload
      </Link>
      {!isAuthorized && <LockIcon className="ml-2 h-4 w-4" />}
    </DropdownMenu.Item>
  </DropdownMenu.Content>
</DropdownMenu>
```

**Benefits of this approach**:
- ✅ Keeps header clean and organized
- ✅ Clear visual feedback (grayed out) when auth is required
- ✅ Maintains existing "My Recipes" tab structure
- ✅ Easily extensible for future add methods (e.g., "From Scan", "Import Cookbook")
- ✅ Familiar dropdown pattern
- ✅ Preserves mobile responsiveness

#### 3. File Upload Component

**Component**: `apps/kitchen_mate/frontend/src/components/FileUpload.tsx`

Key features:
- Drag-and-drop zone with visual feedback
- File type validation (client-side preview)
- File size validation
- Progress indicator during upload
- Preview for images before submitting
- Error handling for unsupported formats

```typescript
interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isLoading: boolean;
  acceptedFormats: string[]; // e.g., [".jpg", ".png", ".pdf"]
}
```

#### 4. Auth Integration

Wrap the upload UI with `useRequireAuth`:

```typescript
import { useRequireAuth } from "../hooks/useRequireAuth";

function UploadSection() {
  const { isAuthorized } = useRequireAuth();

  const handleFileUpload = async (file: File) => {
    if (!isAuthorized) {
      // Show sign-in modal or message
      setShowSignInPrompt(true);
      return;
    }

    // Proceed with upload
    await clipRecipeFromUpload(file);
  };

  return (
    <FileUpload
      onFileSelect={handleFileUpload}
      // ... other props
    />
  );
}
```

## Implementation Considerations

### 1. File Storage & Persistence

**Persistent Storage Strategy** (Supabase Storage):

Uploaded files are **permanently stored** alongside user recipes to enable:
- Re-parsing with improved models
- Downloading original files
- Historical tracking of recipe sources

**Storage Architecture**:

```
Supabase Storage Bucket: recipe-uploads
├── {user_id}/
│   ├── {recipe_id}/
│   │   ├── original.{ext}      # Original uploaded file
│   │   └── metadata.json       # Upload metadata
```

**Storage Flow**:
1. User uploads file → Validate and save to temp directory
2. Extract recipe using Claude API → Get `Recipe` object
3. Upload file to Supabase Storage → Get permanent URL
4. Save to database:
   - `recipes` table: recipe data, parsing method
   - `user_recipes` table: user's copy, tags, notes
   - `recipe_uploads` table: file metadata, storage path

**Database Schema Changes**:

Add new table `recipe_uploads`:

```sql
CREATE TABLE recipe_uploads (
  id TEXT PRIMARY KEY,
  recipe_id TEXT NOT NULL REFERENCES recipes(id),
  user_id TEXT NOT NULL,
  file_type TEXT NOT NULL CHECK (file_type IN ('image', 'document')),
  file_extension TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  file_size_bytes INTEGER NOT NULL,
  storage_path TEXT NOT NULL,
  storage_url TEXT NOT NULL,
  file_hash TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  UNIQUE(recipe_id)
);

CREATE INDEX idx_recipe_uploads_recipe_id ON recipe_uploads(recipe_id);
CREATE INDEX idx_recipe_uploads_user_id ON recipe_uploads(user_id);
CREATE INDEX idx_recipe_uploads_file_hash ON recipe_uploads(file_hash);
```

**Configuration**:

Add to `config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Supabase Storage (for file uploads)
    supabase_storage_url: str | None = None
    supabase_service_role_key: str | None = None  # For backend storage operations
    recipe_uploads_bucket: str = "recipe-uploads"
```

**File Upload Module** (`storage.py`):

```python
"""Supabase Storage integration for uploaded recipes."""

from pathlib import Path
from supabase import create_client, Client

async def upload_recipe_file(
    user_id: str,
    recipe_id: str,
    file_path: Path,
    original_filename: str,
    supabase_url: str,
    supabase_key: str,
    bucket: str,
) -> tuple[str, str]:
    """Upload file to Supabase Storage.

    Args:
        user_id: User ID
        recipe_id: Recipe ID
        file_path: Local file path
        original_filename: Original filename
        supabase_url: Supabase project URL
        supabase_key: Service role key
        bucket: Storage bucket name

    Returns:
        Tuple of (storage_path, storage_url)
    """
    client: Client = create_client(supabase_url, supabase_key)

    # Generate storage path
    ext = Path(original_filename).suffix
    storage_path = f"{user_id}/{recipe_id}/original{ext}"

    # Upload file
    with open(file_path, "rb") as f:
        client.storage.from_(bucket).upload(
            storage_path,
            f,
            file_options={"content-type": get_mime_type(ext)}
        )

    # Get public URL
    storage_url = client.storage.from_(bucket).get_public_url(storage_path)

    return storage_path, storage_url


async def download_recipe_file(
    storage_path: str,
    supabase_url: str,
    supabase_key: str,
    bucket: str,
) -> bytes:
    """Download file from Supabase Storage.

    Args:
        storage_path: Path in storage bucket
        supabase_url: Supabase project URL
        supabase_key: Service role key
        bucket: Storage bucket name

    Returns:
        File content as bytes
    """
    client: Client = create_client(supabase_url, supabase_key)
    return client.storage.from_(bucket).download(storage_path)


async def delete_recipe_file(
    storage_path: str,
    supabase_url: str,
    supabase_key: str,
    bucket: str,
) -> None:
    """Delete file from Supabase Storage.

    Args:
        storage_path: Path in storage bucket
        supabase_url: Supabase project URL
        supabase_key: Service role key
        bucket: Storage bucket name
    """
    client: Client = create_client(supabase_url, supabase_key)
    client.storage.from_(bucket).remove([storage_path])
```

**Fallback for Single-Tenant Mode**:

When Supabase Storage is not configured, store files locally:

```python
# In config.py
local_uploads_dir: Path = Path("./uploads")

# In storage.py - check if supabase_storage_url is set
if not settings.supabase_storage_url:
    # Use local filesystem storage
    storage_path = settings.local_uploads_dir / user_id / recipe_id / f"original{ext}"
    storage_url = f"/api/uploads/{user_id}/{recipe_id}/original{ext}"
```

### 2. Re-Parsing Functionality

Allow users to re-extract recipes from stored files when improvements are made to the parsing models.

**API Endpoint**: `POST /me/recipes/{id}/reparse`

```python
@router.post("/me/recipes/{id}/reparse")
async def reparse_recipe(
    id: str,
    user: Annotated[User, Depends(get_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GetUserRecipeResponse:
    """Re-extract recipe from original uploaded file.

    Only works for recipes that were created from uploads.
    Returns updated recipe data.
    """
    # Get user recipe
    user_recipe = await get_user_recipe(id, user.id)

    # Get upload record
    upload = await get_recipe_upload(user_recipe.recipe_id)
    if not upload:
        raise HTTPException(
            status_code=400,
            detail="Recipe was not created from an upload",
        )

    # Download file from storage
    file_content = await download_recipe_file(
        upload.storage_path,
        settings.supabase_storage_url,
        settings.supabase_service_role_key,
        settings.recipe_uploads_bucket,
    )

    # Save to temp file
    temp_file = Path(tempfile.mktemp(suffix=upload.file_extension))
    temp_file.write_bytes(file_content)

    try:
        # Re-parse based on file type
        if upload.file_type == "image":
            recipe = parse_recipe_from_image(
                temp_file,
                api_key=settings.anthropic_api_key,
            )
        else:
            recipe = parse_recipe_from_document(
                temp_file,
                api_key=settings.anthropic_api_key,
            )

        # Update user recipe with new data
        await update_user_recipe(
            user_recipe_id=id,
            user_id=user.id,
            recipe=recipe,
        )

        return await get_user_recipe_with_lineage(id, user.id)

    finally:
        temp_file.unlink()
```

**Frontend Integration**:

Add "Re-parse" button to recipe view for uploaded recipes:

```typescript
// In SavedRecipeView.tsx
{recipe.source_type === "upload" && (
  <button
    onClick={handleReparse}
    className="text-sm text-coral hover:underline"
  >
    🔄 Re-parse with latest model
  </button>
)}
```

### 3. File Download Endpoint

Allow users to download their original uploaded files.

**API Endpoint**: `GET /me/recipes/{id}/download`

```python
@router.get("/me/recipes/{id}/download")
async def download_recipe_file_endpoint(
    id: str,
    user: Annotated[User, Depends(get_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    """Download the original uploaded file for a recipe.

    Returns the file as a downloadable attachment.
    """
    # Get user recipe
    user_recipe = await get_user_recipe(id, user.id)

    # Get upload record
    upload = await get_recipe_upload(user_recipe.recipe_id)
    if not upload:
        raise HTTPException(
            status_code=404,
            detail="No uploaded file found for this recipe",
        )

    # Download file from storage
    file_content = await download_recipe_file(
        upload.storage_path,
        settings.supabase_storage_url,
        settings.supabase_service_role_key,
        settings.recipe_uploads_bucket,
    )

    # Return as streaming response
    return StreamingResponse(
        BytesIO(file_content),
        media_type=upload.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{upload.original_filename}"'
        },
    )
```

**Frontend Integration**:

Add download link to recipe view:

```typescript
{recipe.has_upload && (
  <a
    href={`/api/me/recipes/${recipe.id}/download`}
    download
    className="text-sm text-coral hover:underline"
  >
    📥 Download original file
  </a>
)}
```

### 4. Rate Limiting

Uploaded files use Claude API for every request (no cache like URL-based clipping):

- Implement per-user rate limiting for uploads
- Consider daily/monthly quotas for multi-tenant mode
- Track usage by user ID

**Suggested limits**:
- 10 uploads per hour per user
- 100 uploads per month per user (free tier)

### 3. Cost Management

Claude API calls for vision/document processing cost more than text-only:

- Track API usage per user
- Consider adding usage dashboard
- Optionally charge for upload feature (premium)
- Set organization-wide budgets

### 4. Security Considerations

**File Validation**:
- ✅ Extension checking (already implemented)
- ✅ Size limits (10MB images, 20MB documents)
- ⚠️ Content-type verification (check actual file magic bytes)
- ⚠️ Virus scanning for multi-tenant production

**User Isolation**:
- ✅ User-gated endpoint (requires auth in multi-tenant)
- ✅ Temp files cleaned up immediately
- ✅ No file paths exposed to client

**Recommendations**:
1. Add magic byte validation to `validate_file_extension()`
2. Integrate virus scanning service (e.g., ClamAV) for production
3. Add file upload audit logging

### 5. Error Handling

**Client-side**:
- Validate file type before upload (instant feedback)
- Show file size errors before sending
- Progress indicator for large files
- Graceful degradation if feature unavailable

**Server-side**:
- Return specific error codes:
  - `400`: Invalid file format or size
  - `401`: Authentication required (multi-tenant)
  - `503`: API key not configured
  - `500`: Extraction failed
- Log extraction failures with file metadata (but not content)

### 6. User Experience Enhancements

**Image Preview**:
- Show thumbnail before extracting
- Allow cropping/rotation if recipe is partial
- Highlight detected text regions (future)

**Progress Feedback**:
- Upload progress bar
- Extraction status ("Analyzing image...", "Extracting recipe...")
- Estimated time remaining for large PDFs

**Batch Upload** (Future):
- Upload multiple images/PDFs at once
- Extract multiple recipes in parallel
- Bulk save to collection

### 7. Testing Strategy

**Unit Tests**:
- `test_files.py`: File validation, size checks, hash computation
- Mock `UploadFile` for upload handling tests

**Integration Tests**:
- Upload actual test images (sample recipe photos)
- Upload test PDFs
- Verify correct parser selection
- Test auth requirement in multi-tenant mode

**Test Fixtures**:
```
tests/fixtures/
  ├── images/
  │   ├── cookbook_page.jpg
  │   ├── recipe_card.png
  │   └── handwritten_recipe.jpg
  └── documents/
      ├── recipe.pdf
      ├── recipe.docx
      └── recipe.txt
```

## Implementation Steps

### Phase 1: Database & Storage Setup

1. **Database Schema**:
   - [ ] Create migration for `recipe_uploads` table
   - [ ] Add SQLAlchemy model `RecipeUploadModel` in `database/models.py`
   - [ ] Add repository functions in `database/repositories.py`:
     - `save_recipe_upload()`
     - `get_recipe_upload()`
     - `delete_recipe_upload()`

2. **Storage Integration**:
   - [ ] Add Supabase Storage config to `config.py`
   - [ ] Create `storage.py` module with:
     - `upload_recipe_file()`
     - `download_recipe_file()`
     - `delete_recipe_file()`
   - [ ] Implement local filesystem fallback for single-tenant mode
   - [ ] Set up Supabase Storage bucket (in Supabase dashboard)

3. **Configuration**:
   - [ ] Add `SUPABASE_STORAGE_URL` to `.env.example`
   - [ ] Add `SUPABASE_SERVICE_ROLE_KEY` to `.env.example`
   - [ ] Update README with storage configuration instructions

### Phase 2: Backend File Upload

4. **File Handling**:
   - [ ] Create `files.py` module with:
     - `validate_file_extension()`
     - `validate_file_size()`
     - `save_upload_to_temp()`
     - `compute_file_hash()`
   - [ ] Write unit tests for file validation

5. **Upload Endpoint**:
   - [ ] Add upload schemas to `schemas.py`:
     - `ClipUploadResponse`
     - Update `GetUserRecipeResponse` to include upload info
   - [ ] Create `routes/upload.py` with `POST /clip/upload`
   - [ ] Integrate with storage module
   - [ ] Add auth gating with `get_user` dependency
   - [ ] Write integration tests with test fixtures

6. **Re-parsing Endpoint**:
   - [ ] Add `POST /me/recipes/{id}/reparse` to `routes/me.py`
   - [ ] Add repository function `get_recipe_upload_by_recipe_id()`
   - [ ] Write tests for re-parsing logic

7. **Download Endpoint**:
   - [ ] Add `GET /me/recipes/{id}/download` to `routes/me.py`
   - [ ] Implement StreamingResponse for file downloads
   - [ ] Test with various file types

### Phase 3: Frontend - Header Navigation

8. **Dropdown Component**:
   - [ ] Install/create dropdown menu component (or use headlessui)
   - [ ] Update `Header.tsx`:
     - Replace "Clip Recipe" link with dropdown
     - Add "Add Recipe" dropdown trigger
     - Add "From Web" and "From Upload" menu items
     - Disable "From Upload" when not authorized
   - [ ] Add lock icon for disabled state
   - [ ] Add tooltip for disabled upload option

9. **Routing**:
   - [ ] Create `/upload` route in `App.tsx`
   - [ ] Keep existing `/clip` route for URL-based clipping

### Phase 4: Frontend - Upload UI

10. **File Upload Component**:
    - [ ] Create `FileUpload.tsx`:
      - Drag-and-drop zone
      - File picker button
      - File type validation
      - File size validation
      - Image preview
      - Upload progress
    - [ ] Add auth integration with `useRequireAuth`
    - [ ] Show sign-in modal if not authorized

11. **Upload Page**:
    - [ ] Create `UploadRecipePage.tsx`
    - [ ] Integrate `FileUpload` component
    - [ ] Handle upload response
    - [ ] Show extracted recipe
    - [ ] Add save to collection flow

12. **API Client**:
    - [ ] Add `clipRecipeFromUpload()` to `api/clip.ts`
    - [ ] Add `reparseRecipe()` function
    - [ ] Handle progress callbacks

### Phase 5: Recipe View Enhancements

13. **Upload Indicators**:
    - [ ] Update `SavedRecipeView.tsx`:
      - Show upload source badge for uploaded recipes
      - Add "Re-parse" button (if from upload)
      - Add "Download original" link (if from upload)
    - [ ] Update `UserRecipeSummaryResponse` to include upload flag

14. **Recipe List**:
    - [ ] Add upload indicator icon to recipe cards
    - [ ] Filter by source type (web vs upload)

### Phase 6: Enhancement & Polish

15. **Rate Limiting**:
    - [ ] Add rate limiting middleware for upload endpoint
    - [ ] Track uploads per user
    - [ ] Return 429 when limit exceeded

16. **Error Handling**:
    - [ ] Client-side validation errors
    - [ ] Server-side extraction errors
    - [ ] Storage errors (quota exceeded, etc.)
    - [ ] Graceful degradation when storage unavailable

17. **Testing**:
    - [ ] Add test fixtures (sample images, PDFs)
    - [ ] Integration tests for upload flow
    - [ ] Test re-parsing
    - [ ] Test file downloads
    - [ ] Test auth gating

18. **Documentation**:
    - [ ] Update README with upload feature
    - [ ] Add Supabase Storage setup guide
    - [ ] Document rate limits
    - [ ] Add troubleshooting section

### Phase 7: Production Hardening

19. **Security**:
    - [ ] Add magic byte validation
    - [ ] Integrate virus scanning (optional)
    - [ ] Add file upload audit logging
    - [ ] Test with malicious files

20. **Monitoring**:
    - [ ] Track API costs for vision/document calls
    - [ ] Set up alerts for high usage
    - [ ] Add usage dashboard for admins

21. **Performance**:
    - [ ] Load testing with large files
    - [ ] Optimize storage upload/download
    - [ ] Add caching for download endpoints

## MVP: Upload → Preview → Save (Revised)

### Overview

The MVP supports all file types but **does not persist uploaded files**. Files are processed in-memory, extracted recipes are returned for user review, and only saved to the database when the user explicitly saves.

This matches the existing URL-based flow: **Clip → Review → Save**

### MVP Scope

**Included**:
- All supported file types (jpg, png, gif, webp, pdf, docx, txt, md)
- Magic byte validation for security
- Recipe extraction via Claude API
- Preview extracted recipe before saving
- User can modify recipe before saving
- Save to existing `recipes` + `user_recipes` tables

**Excluded (Future Phases)**:
- File persistence / storage infrastructure
- Re-parsing functionality
- Original file downloads
- Supabase Storage integration

### MVP Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│   Upload    │────▶│   Extract    │────▶│   Preview   │────▶│   Save   │
│   File      │     │   Recipe     │     │   & Edit    │     │  (POST)  │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────┘
     │                    │                    │                   │
     ▼                    ▼                    ▼                   ▼
  Validate           Claude API          Frontend only       Database
  (magic bytes)      (no storage)        (user reviews)      (recipes +
                                                              user_recipes)
```

### MVP API Design

#### `POST /api/clip/upload` — Extract Recipe from File (No Persistence)

Extract a recipe from an uploaded file. Returns the extracted recipe for preview. **Does not save anything to database.**

**Request**: `multipart/form-data` with `file` field

**Response** (200 OK):
```json
{
  "recipe": {
    "title": "Chocolate Cake",
    "ingredients": [...],
    "instructions": [...],
    ...
  },
  "file_info": {
    "filename": "cookbook_page.jpg",
    "file_type": "image",
    "file_size_bytes": 1234567,
    "content_type": "image/jpeg"
  },
  "parsing_method": "llm_image"
}
```

**Error Responses**:
- `400`: Invalid file format, size exceeded, or content mismatch
- `401`: Authentication required (multi-tenant mode)
- `503`: Anthropic API key not configured
- `422`: Failed to extract recipe from file

#### `POST /api/me/recipes` — Save Recipe (Updated)

The existing save endpoint is updated to accept recipe data directly for uploads:

```json
{
  "recipe": { ... },           // Extracted (and possibly modified) recipe
  "source_type": "upload",     // New field to indicate source
  "source_filename": "cookbook_page.jpg",
  "parsing_method": "llm_image",
  "tags": ["dessert"],
  "notes": "From grandma's cookbook"
}
```

### MVP Implementation Checklist

#### Phase 1: Backend

- [ ] Create `files.py` with magic byte validation
  - [ ] `detect_file_type()` - magic byte detection
  - [ ] `validate_file_size()` - size limits
  - [ ] `process_upload()` - combined validation
  - [ ] Unit tests for all file types + edge cases

- [ ] Add upload endpoint to `routes/clip.py`
  - [ ] `POST /api/clip/upload` - extract only, no persistence
  - [ ] Proper async wrapping for sync parsers
  - [ ] Temp file cleanup in finally block

- [ ] Update `schemas.py`
  - [ ] `FileInfo` - upload metadata
  - [ ] `ClipUploadResponse` - extraction response
  - [ ] Update `SaveRecipeRequest` for upload source

- [ ] Update `routes/me.py`
  - [ ] Handle `source_type: "upload"` in save endpoint
  - [ ] Generate `upload://` source URL from recipe hash

- [ ] Tests
  - [ ] Test file validation (valid + invalid files)
  - [ ] Test upload endpoint with mock files
  - [ ] Test save flow for uploaded recipes

#### Phase 2: Frontend

- [ ] Header dropdown navigation
  - [ ] "Add Recipe" dropdown with "From Web" / "From Upload"
  - [ ] Auth gating for upload option

- [ ] Upload page (`/upload`)
  - [ ] File drop zone component
  - [ ] Client-side validation (type + size)
  - [ ] Loading state during extraction
  - [ ] Error handling

- [ ] Recipe preview/edit component
  - [ ] Display extracted recipe
  - [ ] Inline editing for all fields
  - [ ] Tags and notes input
  - [ ] Cancel / Save buttons

- [ ] API client
  - [ ] `uploadAndExtractRecipe(file)` → preview
  - [ ] Update `saveRecipe()` for upload source

### Future Phases (Post-MVP)

**Phase 3: File Persistence**
- Supabase Storage integration
- `recipe_uploads` table
- Re-parsing functionality
- Original file downloads

**Phase 4: Enhanced Features**
- Batch upload (multiple files)
- PDF page selection
- Image cropping before extraction
- Rate limiting

---

## Open Questions

1. **File deduplication across users?**
   - **Question**: If two users upload the same cookbook photo, should we dedupe?
   - **Consideration**: File hash matching could save storage costs
   - **Privacy**: Need to ensure no cross-user data leakage
   - **Recommendation**: Start with per-user storage, add deduplication later if needed

2. **Should we support batch upload initially?**
   - **Recommendation**: No, add in Phase 8 based on user feedback
   - **Reason**: Single upload flow is simpler to implement and test

3. **PDF page limits?**
   - **Question**: What's the max PDF page count to prevent abuse?
   - **Recommendation**: 10 pages max initially (prevents abuse, most recipes are 1-2 pages)
   - **Future**: Allow more pages for premium users

4. **Storage quota per user?**
   - **Question**: Should we limit total storage per user?
   - **Recommendation**:
     - Free tier: 100 uploads or 500MB total
     - Premium: Unlimited uploads or 5GB total
   - **Implementation**: Track in `recipe_uploads` table

5. **Re-parsing notifications?**
   - **Question**: Should we notify users when better parsing models are available?
   - **Recommendation**: Add "Model update available" badge on uploaded recipes
   - **Future**: Batch re-parse all uploaded recipes when model improves

6. **Original file retention policy?**
   - **Question**: Keep files forever or delete after some time?
   - **Recommendation**:
     - Keep files while recipe exists in user's collection
     - Delete file when user deletes recipe (with 30-day grace period)
     - Add "Delete original file" option to save storage

7. **Local storage for single-tenant mode?**
   - **Question**: Where to store files when Supabase Storage isn't configured?
   - **Recommendation**: `./uploads/` directory with same structure
   - **Consideration**: Document backup strategies for local deployments

## Success Metrics

- Number of uploads per user per month
- Upload success rate (successful extractions / total uploads)
- Average extraction time by file type
- User satisfaction (feature rating)
- API cost per upload

## Related Features

This feature enables future enhancements:

- **Recipe OCR Improvements**: Train custom models on cookbook layouts
- **Batch Processing**: Upload entire cookbooks
- **Photo Organization**: Tag and organize recipe photos
- **Offline Mode**: Extract recipes without internet (local OCR)
- **Recipe Editing**: Fix extraction errors inline
