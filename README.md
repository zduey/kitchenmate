# Recipe Clipper Monorepo

This is a monorepo containing the Recipe Clipper project components.

## Repository Structure

```
recipe-clipper/
├── apps/                          # Applications
│   └── recipe_manager/           # Web application (coming soon)
│
└── packages/                      # Reusable libraries
    └── recipe_clipper/           # Recipe clipper library + CLI
```

## Packages

### [recipe-clipper](./packages/recipe_clipper/)

Python library and CLI tool for extracting recipes from websites.

- **Library**: Extract recipes programmatically from 100+ websites
- **CLI**: Command-line tool with text, JSON, and Markdown output formats
- **Supported Sites**: Uses [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) for broad website support

See [packages/recipe_clipper/README.md](./packages/recipe_clipper/README.md) for installation and usage instructions.

## Development

This monorepo uses [uv](https://github.com/astral-sh/uv) for dependency management.

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

## License

MIT
