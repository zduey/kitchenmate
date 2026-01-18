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
```

### Running the CLI

```bash
uv run --directory packages/recipe_clipper recipe-clipper <URL>
```

### Running the Backend

```bash
# Development server
uv run --directory apps/kitchen_mate uvicorn kitchen_mate.main:app --reload

# Using Docker
docker compose up --build
```

## Deployment Modes

Kitchen Mate supports two deployment modes:

### Single-Tenant (Self-Hosted)

Run your own instance with no authentication required. All features are available to anyone with access.

```bash
# No Supabase configuration needed - just run the app
docker compose up --build
```

### Multi-Tenant (SaaS)

Deploy as a multi-tenant service with Supabase authentication. Public features (clip, export) work for everyone; user-specific features require sign-in.

```bash
# Set Supabase environment variables
export SUPABASE_JWT_SECRET="your-jwt-secret"
export VITE_SUPABASE_URL="https://your-project.supabase.co"
export VITE_SUPABASE_ANON_KEY="your-anon-key"
```

The mode is determined automatically by whether `SUPABASE_JWT_SECRET` is set.

### Testing

```bash
# Library tests
uv run --directory packages/recipe_clipper pytest

# Backend tests
uv run --directory apps/kitchen_mate pytest
```