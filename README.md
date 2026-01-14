# Kitchen Mate

A monorepo for recipe extraction tools and services.

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

### Testing

```bash
# Library tests
uv run --directory packages/recipe_clipper pytest

# Backend tests
uv run --directory apps/kitchen_mate pytest
```