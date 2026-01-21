# Design Document: Image & Document Recipe Clipping

## Overview

This feature extends Kitchen Mate's recipe extraction capabilities to support uploaded images and documents (PDF, DOCX, etc.) in addition to URLs. Users can extract recipes from:

- **Images**: Cookbook photos, recipe cards, handwritten notes, screenshots
- **Documents**: PDF cookbooks, Word documents, text files

This is a **user-gated feature** requiring authentication in multi-tenant mode, while remaining available in single-tenant deployments.

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

Add new request/response schemas to `apps/kitchen_mate/src/kitchen_mate/schemas.py`:

```python
class ClipUploadResponse(BaseModel):
    """Response body for the /clip/upload endpoint."""

    recipe: Recipe = Field(description="The extracted recipe")
    source_type: str = Field(description="Type of source: 'image' or 'document'")
    original_filename: str = Field(description="Original uploaded filename")
    file_hash: str = Field(description="SHA-256 hash of uploaded file")
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


@router.post("/clip/upload")
async def clip_from_upload(
    file: Annotated[UploadFile, File(description="Recipe image or document")],
    user: Annotated[User, Depends(get_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClipUploadResponse:
    """Extract a recipe from an uploaded image or document.

    This is a user-gated endpoint:
    - Single-tenant: Available to all (uses DEFAULT_USER)
    - Multi-tenant: Requires authentication

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
        # Validate and save upload
        temp_file = await save_upload_to_temp(file)

        # Determine file type
        _, file_type = validate_file_extension(file.filename or "")

        # Compute file hash for deduplication
        file_hash = compute_file_hash(temp_file)

        # Parse based on type
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

        logger.info(
            "Extracted recipe from %s for user %s: %s",
            file_type,
            user.id,
            recipe.title,
        )

        return ClipUploadResponse(
            recipe=recipe,
            source_type=file_type,
            original_filename=file.filename or "unknown",
            file_hash=file_hash,
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

Add to `apps/kitchen_mate/frontend/src/api/clip.ts`:

```typescript
export interface ClipUploadResponse {
  recipe: Recipe;
  source_type: "image" | "document";
  original_filename: string;
  file_hash: string;
}

export async function clipRecipeFromUpload(
  file: File,
  onProgress?: (progress: number) => void
): Promise<ClipUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/clip/upload", {
    method: "POST",
    body: formData,
    credentials: "include", // Include auth cookies
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to clip recipe from upload");
  }

  return response.json();
}
```

#### 2. UI Component Options

Three design options for the upload interface:

##### **Option A: Unified Input with Tab Switcher** (Recommended)

Replace the current single URL input with a tabbed interface:

```
┌─────────────────────────────────────────────────┐
│  [ URL ]  [ Upload ]                           │
├─────────────────────────────────────────────────┤
│                                                 │
│  [  Drag & drop or click to upload  ]          │
│                                                 │
│  Supports: Images (JPG, PNG) & PDFs            │
└─────────────────────────────────────────────────┘
```

**Pros**:
- Clear separation between URL and upload workflows
- Familiar pattern (tabs)
- Doesn't clutter the main interface
- Easy to add more input types later

**Cons**:
- Requires switching tabs
- Takes slightly more clicks for first-time users

##### **Option B: Combined Input with Auto-Detection**

Single input that accepts both URLs and files:

```
┌─────────────────────────────────────────────────┐
│  Enter URL or drag & drop file                 │
│  ┌───────────────────────────────────────┐     │
│  │ https://example.com/recipe  [📎]      │     │
│  └───────────────────────────────────────┘     │
│                                    [ Clip ▼ ]  │
└─────────────────────────────────────────────────┘
```

Clicking the paperclip icon opens file picker. Drag-and-drop anywhere on the input.

**Pros**:
- Minimal UI changes
- Single point of entry
- Drag-and-drop convenience

**Cons**:
- Less discoverable for upload feature
- Could be confusing to mix two input types
- Validation complexity (URL vs file)

##### **Option C: Separate Upload Section Below**

Keep URL input as-is, add upload section below:

```
┌─────────────────────────────────────────────────┐
│  Enter recipe URL                              │
│  ┌───────────────────────────────────────┐     │
│  │ https://example.com/recipe            │     │
│  └───────────────────────────────────────┘     │
│                                    [ Clip ▼ ]  │
├─────────────────────────────────────────────────┤
│                    OR                           │
├─────────────────────────────────────────────────┤
│  Upload recipe image or PDF                    │
│  ┌───────────────────────────────────────┐     │
│  │  Drag & drop or click to browse       │     │
│  └───────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

**Pros**:
- Both options always visible
- Very clear and discoverable
- No mode switching

**Cons**:
- Takes more vertical space
- Can feel cluttered on mobile

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

### 1. File Storage

**Temporary Storage Strategy**:
- Files are saved to temp directory during processing
- Cleaned up immediately after extraction (in `finally` block)
- Not persisted to permanent storage
- Uses Python's `tempfile.NamedTemporaryFile` with `delete=False` for explicit control

**Alternative (Future Enhancement)**:
- Store original files in user's collection for re-extraction
- Use cloud storage (S3, Supabase Storage) for persistence
- Enable "re-process with improved model" workflows

### 2. Rate Limiting

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

1. **Backend Foundation**:
   - [ ] Create `files.py` module with upload handling
   - [ ] Add upload schemas to `schemas.py`
   - [ ] Create `routes/upload.py` with `/clip/upload` endpoint
   - [ ] Write unit tests for file validation

2. **Frontend - API Integration**:
   - [ ] Add upload function to API client
   - [ ] Create `FileUpload.tsx` component
   - [ ] Add auth gating with `useRequireAuth`

3. **Frontend - UI Integration** (choose option):
   - [ ] **Option A**: Add tab switcher to `RecipeForm.tsx`
   - [ ] **Option B**: Add upload icon to existing input
   - [ ] **Option C**: Add separate upload section

4. **Enhancement & Polish**:
   - [ ] Add rate limiting middleware
   - [ ] Implement usage tracking
   - [ ] Add file preview for images
   - [ ] Add progress indicators
   - [ ] Write integration tests
   - [ ] Add magic byte validation
   - [ ] Document in README

5. **Production Hardening**:
   - [ ] Add virus scanning
   - [ ] Set up monitoring/alerting for API costs
   - [ ] Add usage dashboard
   - [ ] Load testing with large files

## Open Questions

1. **Should we cache extracted recipes from uploads?**
   - Pro: Avoid re-processing same cookbook pages
   - Con: Need to store file hashes, complex invalidation
   - Recommendation: Start without caching, add if users request

2. **Should we support batch upload initially?**
   - Recommendation: No, add later based on user feedback

3. **What's the max PDF page count?**
   - Recommendation: 10 pages max initially (prevents abuse)

4. **Should uploads auto-save to user's recipe collection?**
   - Recommendation: No, keep upload and save as separate actions (consistency with URL flow)

5. **Which UI option should we implement?**
   - **Recommendation: Option A (Tab Switcher)** - balances discoverability, clarity, and extensibility

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
