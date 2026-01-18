# Recipe Saving Feature - Design Document

## Overview

This document outlines the design for a recipe saving feature that allows authenticated users to save and manage recipes extracted from websites. The design supports a "fork-based" model where recipes are cached globally and users create their own instances that can be modified independently while maintaining lineage tracking.

## Goals

1. Allow users to save recipes to their personal collection
2. Avoid duplicate parsing of the same source URL
3. Track parsing method used (LLM vs recipe-scrapers)
4. Support future recipe modifications while preserving version history
5. Enable sharing of recipe versions between users

## Database Schema

### Table 1: `recipes`

**Purpose**: Store unique recipe sources (URLs from websites)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| `source_url` | TEXT | NOT NULL, UNIQUE | Original recipe URL |
| `source_domain` | TEXT | NOT NULL | Domain extracted from URL (for indexing/filtering) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When source was first discovered |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- `idx_recipes_source_url` on `source_url` (unique)
- `idx_recipes_source_domain` on `source_domain`

**Notes**:
- `source_url` is the canonical identifier for recipes from the web
- Multiple parsed versions can exist for the same source

---

### Table 2: `parsed_recipes`

**Purpose**: Cache parsed recipe data with metadata about parsing method

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| `recipe_id` | UUID | NOT NULL, FOREIGN KEY → recipes(id) ON DELETE CASCADE | Source recipe reference |
| `parsing_method` | TEXT | NOT NULL | 'recipe_scrapers' or 'llm' |
| `recipe_data` | JSONB | NOT NULL | Extracted recipe (Recipe model as JSON) |
| `parsing_metadata` | JSONB | NULL | Optional metadata (model version, extraction time, etc.) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When parsed |
| `parse_success` | BOOLEAN | NOT NULL, DEFAULT TRUE | Whether parsing succeeded |
| `error_message` | TEXT | NULL | Error details if parse_success is false |

**Indexes**:
- `idx_parsed_recipes_recipe_id` on `recipe_id`
- `idx_parsed_recipes_parsing_method` on `parsing_method`
- `idx_parsed_recipes_created_at` on `created_at` (for sorting by freshness)

**Notes**:
- Multiple parsed versions can exist for the same `recipe_id` (e.g., parsed with different methods)
- `recipe_data` stores the full `Recipe` Pydantic model serialized as JSONB
- JSONB allows efficient querying of recipe fields (e.g., search by ingredient)

---

### Table 3: `user_recipes`

**Purpose**: Track recipes saved to user collections with fork lineage

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| `user_id` | UUID | NOT NULL, FOREIGN KEY → auth.users(id) ON DELETE CASCADE | Owner of the recipe |
| `parsed_recipe_id` | UUID | NOT NULL, FOREIGN KEY → parsed_recipes(id) ON DELETE RESTRICT | Original parsed recipe |
| `recipe_data` | JSONB | NOT NULL | User's version of recipe (initially copied from parsed_recipe) |
| `is_modified` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether user has modified the recipe |
| `notes` | TEXT | NULL | User's personal notes |
| `tags` | TEXT[] | NULL | User-defined tags for organization |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When saved to collection |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Last modification timestamp |

**Indexes**:
- `idx_user_recipes_user_id` on `user_id`
- `idx_user_recipes_parsed_recipe_id` on `parsed_recipe_id`
- `idx_user_recipes_tags` using GIN on `tags` (for tag-based filtering)
- `idx_user_recipes_created_at` on `user_id, created_at` (for user's recipe timeline)
- UNIQUE constraint on `(user_id, parsed_recipe_id)` to prevent duplicate saves

**Notes**:
- `recipe_data` is initially a copy of `parsed_recipes.recipe_data`
- When user modifies the recipe, `is_modified` is set to TRUE
- `parsed_recipe_id` maintains the fork lineage - tracks which parsed recipe this was derived from
- `ON DELETE RESTRICT` on `parsed_recipe_id` prevents deletion of parsed recipes that users depend on

---

## Data Flow

### Saving a Recipe (First Time)

1. **User requests to save recipe from URL**
   - Request: `POST /api/recipes/save` with `{ "url": "https://example.com/recipe" }`

2. **Backend checks if source exists**
   - Query: `SELECT id FROM recipes WHERE source_url = ?`
   - If not exists:
     - Insert into `recipes` table
     - Parse recipe (try recipe-scrapers, fallback to LLM if enabled)
     - Insert into `parsed_recipes` table

3. **Backend checks if user already saved this recipe**
   - Query: `SELECT id FROM user_recipes WHERE user_id = ? AND parsed_recipe_id = ?`
   - If exists: Return existing `user_recipe_id`
   - If not exists:
     - Copy `recipe_data` from `parsed_recipes` to new `user_recipes` entry
     - Return new `user_recipe_id`

### Saving a Recipe (Subsequent Times)

1. **Different user saves same URL**
   - Reuse existing `recipes` and `parsed_recipes` entries
   - Create new `user_recipes` entry for this user
   - No duplicate parsing needed

2. **Re-parsing a recipe**
   - If admin/system wants to refresh a recipe:
     - Insert new `parsed_recipes` entry with updated data
     - Keep old `parsed_recipes` entries for lineage
     - Optionally notify users who saved the recipe about updates

### Retrieving User's Recipes

- **List user's collection**: `GET /api/users/me/recipes`
  - Returns all `user_recipes` for authenticated user
  - Includes metadata (source URL, tags, modification status)

- **Get specific recipe**: `GET /api/users/me/recipes/{recipe_id}`
  - Returns full `recipe_data` from `user_recipes`
  - Includes lineage info (original source URL, parsing method)

### Modifying a Recipe

- **Update user's recipe**: `PUT /api/users/me/recipes/{recipe_id}`
  - Update `recipe_data` in `user_recipes` table
  - Set `is_modified = TRUE`
  - Update `updated_at` timestamp

---

## API Endpoints

### Recipe Saving

#### `POST /api/recipes/save`

Save a recipe from a URL to the authenticated user's collection.

**Request Body**:
```json
{
  "url": "https://example.com/recipe",
  "timeout": 10,
  "use_llm_fallback": true,
  "tags": ["dessert", "chocolate"],
  "notes": "From Mom's recommendations"
}
```

**Response** (201 Created):
```json
{
  "user_recipe_id": "uuid",
  "recipe_id": "uuid",
  "parsed_recipe_id": "uuid",
  "source_url": "https://example.com/recipe",
  "parsing_method": "recipe_scrapers",
  "created_at": "2026-01-18T10:00:00Z",
  "is_new": true
}
```

**Response** (200 OK - Already Saved):
```json
{
  "user_recipe_id": "uuid",
  "recipe_id": "uuid",
  "parsed_recipe_id": "uuid",
  "source_url": "https://example.com/recipe",
  "parsing_method": "recipe_scrapers",
  "created_at": "2026-01-10T15:30:00Z",
  "is_new": false
}
```

---

### User Recipe Management

#### `GET /api/users/me/recipes`

List all recipes in the authenticated user's collection.

**Query Parameters**:
- `limit` (int, default: 50): Number of recipes per page
- `offset` (int, default: 0): Pagination offset
- `tags` (string, comma-separated): Filter by tags
- `modified_only` (bool): Show only modified recipes

**Response** (200 OK):
```json
{
  "recipes": [
    {
      "id": "uuid",
      "source_url": "https://example.com/recipe",
      "title": "Chocolate Cake",
      "image_url": "https://...",
      "is_modified": false,
      "tags": ["dessert", "chocolate"],
      "created_at": "2026-01-18T10:00:00Z",
      "updated_at": "2026-01-18T10:00:00Z"
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

---

#### `GET /api/users/me/recipes/{recipe_id}`

Get full details of a specific recipe from user's collection.

**Response** (200 OK):
```json
{
  "id": "uuid",
  "source_url": "https://example.com/recipe",
  "parsing_method": "recipe_scrapers",
  "is_modified": false,
  "notes": "From Mom's recommendations",
  "tags": ["dessert", "chocolate"],
  "recipe": {
    "title": "Chocolate Cake",
    "ingredients": [...],
    "instructions": [...],
    ...
  },
  "lineage": {
    "recipe_id": "uuid",
    "parsed_recipe_id": "uuid",
    "parsed_at": "2026-01-18T09:55:00Z"
  },
  "created_at": "2026-01-18T10:00:00Z",
  "updated_at": "2026-01-18T10:00:00Z"
}
```

---

#### `PUT /api/users/me/recipes/{recipe_id}`

Update a recipe in the user's collection (modify recipe data, notes, or tags).

**Request Body**:
```json
{
  "recipe": {
    "title": "My Modified Chocolate Cake",
    "ingredients": [...],
    "instructions": [...]
  },
  "notes": "Reduced sugar by 25%",
  "tags": ["dessert", "healthy"]
}
```

**Response** (200 OK):
```json
{
  "id": "uuid",
  "is_modified": true,
  "updated_at": "2026-01-18T14:30:00Z"
}
```

---

#### `DELETE /api/users/me/recipes/{recipe_id}`

Remove a recipe from the user's collection.

**Response** (204 No Content)

---

## Technology Stack

### Backend
- **FastAPI**: Existing framework
- **Supabase/PostgreSQL**: Database (already configured per `PHASE2_SETUP.md`)
- **SQLAlchemy** or **Supabase Client**: ORM for database operations
- **Pydantic**: Request/response validation

### Database
- **PostgreSQL 15+**: Supports JSONB, UUID, arrays
- **Supabase**: Provides auth.users table integration

---

## Migration Strategy

### Phase 1: Database Schema
1. Create migration files for three tables
2. Add indexes for performance
3. Add foreign key constraints
4. Test migration rollback

### Phase 2: Backend Models
1. Create SQLAlchemy/Pydantic models for new tables
2. Add repository layer for database operations
3. Update existing `/clip` endpoint to optionally save to database

### Phase 3: API Implementation
1. Implement `POST /api/recipes/save` endpoint
2. Implement user recipe CRUD endpoints
3. Add authentication middleware (Supabase JWT validation)
4. Add API tests

### Phase 4: Frontend Integration
1. Add "Save Recipe" button to RecipeCard component
2. Create "My Recipes" page to view saved recipes
3. Add recipe editing UI
4. Add tags and notes management

---

## Security Considerations

### Authentication
- All recipe saving endpoints require authentication
- Use Supabase JWT tokens for user identification
- Validate user_id from token matches requested user

### Authorization
- Users can only modify/delete their own recipes
- Implement row-level security (RLS) policies in Supabase:
  - `user_recipes`: Users can only SELECT/UPDATE/DELETE their own rows
  - `recipes` and `parsed_recipes`: Public read access, system write only

### Input Validation
- Validate URLs before parsing (prevent SSRF attacks)
- Sanitize user input for notes and tags
- Limit tags array size and individual tag length
- Validate recipe_data JSON schema matches Recipe model

### Rate Limiting
- Limit recipe saves per user per hour (prevent abuse)
- Cache parsed recipes to reduce external requests

---

## Future Enhancements

### Version Sharing (Phase 5+)
- Add `shared_recipes` table for publicly shared recipe versions
- Allow users to publish their modified recipes
- Track forks and attribution (who forked from whom)

### Recipe Collections
- Add `collections` table for organizing recipes into folders/cookbooks
- Many-to-many relationship with `user_recipes`

### Recipe Search
- Full-text search on recipe_data JSONB fields
- Search by ingredients, cooking time, etc.
- Use PostgreSQL text search or dedicated search service

### Social Features
- Recipe ratings and reviews
- User following and recipe feeds
- Recipe recommendations based on saved recipes

### Import/Export
- Bulk import from other recipe apps
- Export user collection as JSON/PDF

---

## Open Questions

1. **Re-parsing Strategy**: Should we automatically re-parse recipes periodically to get updates from source websites?
   - Proposed: Manual re-parse triggered by user or admin

2. **Conflict Resolution**: If a user has modified a recipe and the source is re-parsed, how do we handle conflicts?
   - Proposed: Keep user version unchanged, offer optional merge/update UI

3. **Parsed Recipe Deletion**: Should we ever delete old parsed_recipes entries?
   - Proposed: Keep indefinitely for lineage tracking, implement archival later if needed

4. **Anonymous Recipe Saving**: Should unauthenticated users be able to save recipes (local storage)?
   - Proposed: No, require authentication to reduce scope

5. **Parsing Method Selection**: Should users be able to choose parsing method when saving?
   - Proposed: Use automatic fallback logic (recipe-scrapers → LLM), don't expose choice to users

---

## Implementation Checklist

- [ ] Create database migration files
- [ ] Implement database models (SQLAlchemy/Pydantic)
- [ ] Add Supabase client integration to backend
- [ ] Implement repository layer for database operations
- [ ] Create API endpoints for recipe saving
- [ ] Create API endpoints for user recipe management
- [ ] Add authentication middleware
- [ ] Add unit tests for new models and repositories
- [ ] Add integration tests for API endpoints
- [ ] Update frontend RecipeCard with save functionality
- [ ] Create "My Recipes" page in frontend
- [ ] Add recipe editing UI
- [ ] Add tags and notes management UI
- [ ] Update API documentation
- [ ] Update CLAUDE.md with new architecture details
- [ ] Update deployment configuration if needed

---

## Timeline Considerations

This is a substantial feature that will require implementation across multiple layers:
- Database layer: Schema and migrations
- Backend layer: Models, repositories, API endpoints, auth
- Frontend layer: UI components, state management, routing
- Testing: Unit, integration, and E2E tests

Breaking this into phases allows for incremental delivery and validation.

---

## References

- Existing authentication: `PHASE2_SETUP.md`, `PHASE4_COMPLETION.md`
- Current database: Supabase PostgreSQL
- Recipe model: `packages/recipe_clipper/src/recipe_clipper/models.py`
- Backend API: `apps/kitchen_mate/src/kitchen_mate/`
- Frontend: `apps/kitchen_mate/frontend/`
