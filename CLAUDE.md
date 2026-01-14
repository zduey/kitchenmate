# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Kitchen Mate** is a monorepo for extracting recipes from websites. It contains:

- **Library Package** (`packages/recipe_clipper/`): Reusable Python library for recipe extraction
- **CLI Tool**: Command-line interface included with the library package
- **Backend API** (`apps/kitchen_mate/`): FastAPI backend for recipe extraction
- **Frontend SPA** (`apps/kitchen_mate/frontend/`): React single-page application

## Monorepo Structure

```
kitchenmate/
├── .github/workflows/         # CI/CD workflows
├── apps/                      # Applications
│   └── kitchen_mate/         # Full-stack application
│       ├── src/kitchen_mate/        # FastAPI backend
│       │   ├── __init__.py
│       │   ├── main.py              # FastAPI app entry point
│       │   ├── config.py            # Settings management
│       │   ├── schemas.py           # Request/response models
│       │   └── routes/
│       │       └── clip.py          # /clip endpoint
│       ├── frontend/                # React SPA
│       │   ├── src/
│       │   │   ├── main.tsx         # React entry point
│       │   │   ├── App.tsx          # Main application component
│       │   │   ├── components/      # UI components
│       │   │   ├── api/             # API client
│       │   │   └── types/           # TypeScript types
│       │   ├── package.json
│       │   ├── vite.config.ts
│       │   └── tsconfig.json
│       ├── tests/
│       ├── Dockerfile
│       └── pyproject.toml
├── packages/                  # Reusable libraries
│   └── recipe_clipper/       # Main library + CLI
│       ├── src/recipe_clipper/
│       │   ├── __init__.py          # Public API (clip_recipe)
│       │   ├── cli.py               # CLI implementation
│       │   ├── clipper.py           # Main orchestration
│       │   ├── models.py            # Pydantic data models
│       │   ├── exceptions.py        # Custom exceptions
│       │   ├── http.py              # HTTP client
│       │   ├── formatters.py        # Output formatters
│       │   └── parsers/             # Parser implementations
│       ├── tests/
│       ├── pyproject.toml
│       └── README.md
├── docker-compose.yml         # Docker orchestration
├── pyproject.toml             # Root workspace configuration
├── uv.lock                    # Dependency lock file
├── README.md                  # Repository overview
└── CLAUDE.md                  # This file
```

## Architecture and Design Principles

### Pure Functional Design

The library uses pure functions for core logic:

- **No classes for business logic**: All operations are pure functions
- **Function composition**: Complex operations built from simple functions
- **Explicit dependencies**: All dependencies passed as function parameters
- **Immutable data**: Pydantic models with `frozen=True`

### Component Layers

1. **Models** (`models.py`): Immutable Pydantic models
   - `Recipe`, `Ingredient`, `RecipeMetadata`
   - All models inherit from `ImmutableBaseModel`

2. **HTTP Client** (`http.py`): Pure functions for fetching URLs
   - `fetch_url(url, timeout, headers) -> HttpResponse`
   - Returns Pydantic `HttpResponse` model

3. **Parsers** (`parsers/`): Pure functions for parsing HTML
   - `parse_with_recipe_scrapers(response) -> Recipe`
   - Uses [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) library

4. **Orchestration** (`clipper.py`): Composes parsers in fallback chain
   - `clip_recipe(url, timeout) -> Recipe`
   - Fetches HTML → Tries recipe-scrapers

5. **Formatters** (`formatters.py`): Pure functions for output formatting
   - `format_recipe_text(recipe) -> str`
   - `format_recipe_json(recipe) -> str`
   - `format_recipe_markdown(recipe) -> str`

6. **CLI** (`cli.py`): Typer-based command-line interface
   - Single command (default): `recipe-clipper <URL>`
   - Options: `--format`, `--output`, `--timeout`

### Backend API (`apps/kitchen_mate/`)

The FastAPI backend provides HTTP access to recipe extraction:

- **Main App** (`main.py`): FastAPI application with uvicorn server
- **Config** (`config.py`): Settings management with pydantic-settings
- **Schemas** (`schemas.py`): Request/response Pydantic models
- **Routes** (`routes/clip.py`): Recipe clipping endpoint

**Endpoint: `POST /clip`**

Extracts a recipe from a URL and returns JSON.

Request body:
```json
{
  "url": "https://example.com/recipe",
  "timeout": 10,              // HTTP timeout in seconds
  "use_llm_fallback": true    // Enable LLM fallback (default)
}
```

**Endpoint: `POST /convert`**

Converts a recipe to text or markdown format.

Request body:
```json
{
  "recipe": { ... },          // Recipe object from /clip
  "format": "text"            // "text" | "markdown"
}
```

### Frontend SPA (`apps/kitchen_mate/frontend/`)

The React frontend provides a web interface for recipe extraction:

- **Stack**: React 18 + TypeScript + Vite + Tailwind CSS
- **Components**:
  - `App.tsx`: Main application with state management
  - `RecipeForm.tsx`: URL input form
  - `RecipeCard.tsx`: Recipe display with download options
  - `LoadingSpinner.tsx`: Loading state indicator
  - `ErrorMessage.tsx`: Error display
- **API Client** (`api/clip.ts`): Handles recipe extraction requests
- **Development**: Vite dev server with API proxy to backend

### Public API

Only `clip_recipe` is exported at the top level:

```python
from recipe_clipper import clip_recipe

recipe = clip_recipe("https://example.com/recipe", timeout=10)
```

Other components are imported from their modules:

```python
from recipe_clipper.models import Recipe
from recipe_clipper.formatters import format_recipe_markdown
```

## Development Commands

### Environment Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies
uv sync --all-extras
```

### Running the CLI

```bash
# From repository root
uv run --directory packages/recipe_clipper recipe-clipper <URL>

# With options
uv run --directory packages/recipe_clipper recipe-clipper <URL> --format json
uv run --directory packages/recipe_clipper recipe-clipper <URL> --format markdown -o recipe.md
```

### Running the Backend

```bash
# Start the development server
uv run --directory apps/kitchen_mate uvicorn kitchen_mate.main:app --reload

# Or using Docker
docker compose up --build
```

### Running the Frontend

```bash
# Navigate to frontend directory
cd apps/kitchen_mate/frontend

# Install dependencies (first time only)
npm install

# Start development server (port 5173)
npm run dev

# Build for production
npm run build

# Run linting
npm run lint
```

**Note**: The Vite dev server proxies API requests to the backend at `http://localhost:8000`.

### Testing

```bash
# Run library tests
uv run --directory packages/recipe_clipper pytest

# Run backend tests
uv run --directory apps/kitchen_mate pytest

# Run specific test file
uv run pytest packages/recipe_clipper/tests/test_clipper.py -v

# Run with coverage
uv run --directory packages/recipe_clipper pytest --cov=recipe_clipper --cov-report=html

# Run only unit tests (skip integration tests)
uv run --directory packages/recipe_clipper pytest -m "not integration"
```

### Code Quality

```bash
# Format code
uv run ruff format packages/recipe_clipper/src/ packages/recipe_clipper/tests/

# Lint code
uv run ruff check packages/recipe_clipper/src/ packages/recipe_clipper/tests/

# Type check
uv run mypy packages/recipe_clipper/src/
```

## Key Conventions

### Testing

- **Function-based tests**: Use plain functions, not classes
- **Fixtures**: Use pytest fixtures for shared test data
- **Integration tests**: Tests that make real network calls
- **String comparisons**: For formatters, compare full expected output

### Code Style

- **No abbreviations**: Use full words (e.g., `ingredient` not `ing`)
- **Descriptive names**: Clear, self-documenting function names
- **Type hints**: All functions have type annotations
- **Docstrings**: Document public functions with clear descriptions

### Models

- **Immutability**: All models are frozen (cannot be modified after creation)
- **Optional fields**: Use `Optional[Type]` for fields that may be None
- **Field descriptions**: All Pydantic fields have descriptions

### Error Handling

- **Custom exceptions**: Use specific exception types from `exceptions.py`
- **Error messages**: Include context (e.g., URL, error details)
- **Exception chaining**: Use `raise ... from error` to preserve stack traces

## Dependencies

### Core Dependencies

- **recipe-scrapers** (>=15.0.0): Recipe extraction from 100+ websites
- **httpx** (>=0.27.0): HTTP client
- **typer** (>=0.12.0): CLI framework
- **rich** (>=13.0.0): Terminal formatting
- **pydantic** (>=2.0.0): Data validation
- **python-dotenv** (>=1.0.0): Environment variables

### Dev Dependencies

- **pytest** (>=8.0.0): Testing framework
- **pytest-asyncio** (>=0.23.0): Async test support
- **pytest-cov** (>=4.1.0): Coverage reporting
- **respx** (>=0.21.0): HTTP mocking for tests
- **ruff** (>=0.3.0): Linting and formatting
- **mypy** (>=1.8.0): Type checking

## Python Version Support

- **Development**: Python 3.14 (latest)
- **Library compatibility**: Python >=3.9
- **Managed by uv**: Virtual environment with Python 3.14

## CI/CD - GitHub Actions

### Workflow Overview

The repository uses GitHub Actions for continuous integration with smart path filtering:

- **Separate jobs for library, backend, and frontend**: Only runs relevant checks when code changes
- **Path-based triggers**: Uses `dorny/paths-filter` to detect which components changed
- **Lint before test/build**: Ensures code quality before running tests
- **Multi-version testing**: Library tests run on Python 3.9-3.14
- **Docker builds**: Automated image builds pushed to GitHub Container Registry

### Workflow Jobs (ci.yml)

**1. Change Detection** (`changes`)
- Detects which paths changed in the PR/push
- Outputs: `library` and `app` flags
- Triggers appropriate downstream jobs

**2. Library Pipeline** (runs if `packages/recipe_clipper/` changed)
- `library-lint`: Runs ruff format check and lint
- `library-test`: Runs pytest on Python 3.9-3.14
  - Includes coverage reporting
  - Uploads coverage to Codecov

**3. Backend Pipeline** (runs if `apps/kitchen_mate/` changed)
- `app-lint`: Runs ruff format check and lint
- `app-test`: Runs pytest

**4. Frontend Pipeline** (runs if `apps/kitchen_mate/` changed)
- `frontend`: Runs ESLint and builds with Vite (validates TypeScript compilation)

**5. Workspace Checks** (always runs)
- `workspace-lint`: Validates workspace configuration
- Checks `uv.lock` is up to date

**6. Deployment** (runs on push to main after CI passes)
- `deploy`: Triggers Render deploy hook when app code changes

### Path Filters

Changes to these paths trigger library pipeline:
- `packages/recipe_clipper/**`
- `pyproject.toml` (root)
- `uv.lock`

Changes to these paths trigger backend and frontend pipelines:
- `apps/kitchen_mate/**`
- `pyproject.toml` (root)
- `uv.lock`

### CI Workflow Notes

- **Efficiency**: Only runs necessary tests based on changed files
- **Dependencies**: Lint jobs must pass before tests/builds run
- **Coverage**: Only uploaded from Python 3.14 runs
- **Caching**: uv and npm dependencies are cached for faster runs

## Deployment

The application is deployed to [Render](https://render.com) using Docker.

### Configuration

- **`render.yaml`**: Infrastructure as Code blueprint defining the web service
- **Dockerfile**: Multi-stage build (Node for frontend, Python for backend)
- **Deploy hook**: GitHub Actions triggers deployment after CI passes

### Environment Variables (set in Render dashboard)

- `ANTHROPIC_API_KEY`: API key for LLM-based recipe extraction
- `LLM_ALLOWED_IPS`: Comma-separated IPs/CIDR ranges allowed to use LLM fallback

### Deployment Flow

1. Push to `main` branch
2. CI runs (lint, test, build)
3. If CI passes and app code changed, deploy job triggers Render deploy hook
4. Render builds Docker image and deploys

## Development Notes

### Adding New Features

1. Write tests first (TDD approach preferred)
2. Implement pure functions
3. Update type hints and docstrings
4. Run tests and linting
5. Update documentation if needed

### Modifying Existing Code

1. Read the existing implementation first
2. Understand the test coverage
3. Make minimal, focused changes
4. Ensure all tests pass
5. Avoid over-engineering or premature optimization

### Working with Tests

- Use `pytest` fixtures for shared test data
- Function-based tests (not class-based)
- Integration tests should use real network calls
- Mock external dependencies appropriately
