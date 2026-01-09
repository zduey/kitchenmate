# Kitchen Mate

This is a monorepo containing components related to Kitchen Mate.

## Repository Structure

```
kitchen-mate/
├── apps/                          # Applications
│   └── kitchen_mate/           # Web application (coming soon)
│
└── packages/                      # Reusable libraries
    └── recipe_clipper/           # Recipe clipper library + CLI
```

## Packages

### [recipe-clipper](./packages/recipe_clipper/)

Python library and CLI tool for extracting recipes from websites using [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) for broad website support, but falling back to LLM-based parsing (if enabled) for general support.

## Development

This repo uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies
uv sync --all-extras
```

### Common Commands

```bash
# Run the CLI
uv run --directory packages/recipe_clipper recipe-clipper <URL>

# Run tests for the library
uv run --directory packages/recipe_clipper pytest

# Run specific test file
uv run pytest packages/recipe_clipper/tests/test_clipper.py -v
```