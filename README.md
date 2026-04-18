# Kitchen Mate

A monorepo for recipe extraction tools and services. Supports both single-tenant (self-hosted) and multi-tenant (SaaS) deployments.

## Repository Structure

```
kitchenmate/
├── apps/
│   └── kitchen_mate/             # FastAPI backend API
│
└── packages/
    └── recipe_clipper/           # Recipe extraction library + CLI
```

## Components

### [recipe-clipper](./packages/recipe_clipper/)

Python library and CLI tool for extracting recipes from websites using [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) for broad website support, with optional LLM-based fallback parsing.

### [kitchen-mate](./apps/kitchen_mate/)

FastAPI backend that wraps the recipe-clipper library, providing HTTP endpoints for recipe extraction with support for multiple output formats.

## Development

This repo uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies
uv sync --all-extras

# Copy the example env file and fill in values
cp apps/kitchen_mate/.env.example apps/kitchen_mate/.env
```

### Running the CLI

```bash
uv run --directory packages/recipe_clipper recipe-clipper <URL>
```

### Running the Backend

```bash
# Run database migrations
uv run --directory apps/kitchen_mate alembic upgrade head

# Development server
uv run --directory apps/kitchen_mate uvicorn kitchen_mate.main:app --reload

# Using Docker (runs migrations automatically)
docker compose up --build
```

By default, migrations create `kitchenmate.db` in the current directory. Set `CACHE_DB_PATH` to override the location.

### Running the Frontend

```bash
# Install dependencies (first time only)
npm install --prefix apps/kitchen_mate/frontend

# Start development server (port 5173)
npm run dev --prefix apps/kitchen_mate/frontend
```

The Vite dev server proxies API requests to the backend at `http://localhost:8000`, so the backend must be running.

## Deployment Modes

Kitchen Mate supports two deployment modes:

### Single-Tenant (Self-Hosted)

Run your own instance with no authentication required. All features are available to anyone with access. No Supabase configuration needed.

```bash
# Run database migrations
uv run --directory apps/kitchen_mate alembic upgrade head

# Start backend (optional: set ANTHROPIC_API_KEY for LLM-based extraction)
uv run --directory apps/kitchen_mate uvicorn kitchen_mate.main:app --reload

# Start frontend (in a separate terminal)
npm run dev --prefix apps/kitchen_mate/frontend
```

### Multi-Tenant (SaaS)

Deploy as a multi-tenant service with Supabase authentication. Public features (clip, export) work for everyone; user-specific features require sign-in.

Set the following in `apps/kitchen_mate/.env` (see `.env.example`):

```bash
SUPABASE_JWT_SECRET="your-jwt-secret"
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
```

The mode is determined automatically by whether `SUPABASE_JWT_SECRET` is set.

### Testing

```bash
# Library tests
uv run --directory packages/recipe_clipper pytest

# Backend tests
uv run --directory apps/kitchen_mate pytest
```