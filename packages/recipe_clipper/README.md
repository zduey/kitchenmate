# Recipe Clipper

[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/downloads/)
[![codecov](https://codecov.io/gh/zduey/recipe-clipper/branch/master/graph/badge.svg)](https://codecov.io/gh/zduey/recipe-clipper)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/recipe-clipper.svg)](https://pypi.org/project/recipe-clipper/)

Extract recipes from websites, images, and documents with ease. Recipe Clipper supports multiple input sources and uses both web scraping and Claude's vision capabilities to extract structured recipe data.

## Features

- 🌐 **Web Scraping**: Extract recipes from 100+ websites using [recipe-scrapers](https://github.com/hhursev/recipe-scrapers)
- 📸 **Image OCR**: Extract recipes from cookbook photos, recipe cards, or screenshots using Claude's vision API
- 📄 **Document Parsing**: Extract recipes from PDFs, Word documents, text files, and markdown
- 🤖 **LLM Fallback**: Automatically falls back to Claude for unsupported websites
- 🎨 **Multiple Output Formats**: Export as text, JSON, or markdown
- 🔧 **CLI & Library**: Use as a command-line tool or import as a Python library
- ⚡ **Type-Safe**: Full type hints with Pydantic models
- 🔒 **Immutable**: Data models are frozen for safety

## Installation

### Basic Installation

```bash
pip install recipe-clipper
```

This includes:
- Web scraping for 100+ recipe websites
- CLI tool
- All core functionality

### With Claude Support

For image/document parsing and LLM fallback:

```bash
pip install recipe-clipper[llm]
```

## Quick Start

### CLI Usage

#### Extract from a website

```bash
# Basic usage
recipe-clipper clip-webpage https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/

# Save as JSON
recipe-clipper clip-webpage https://example.com/recipe --format json --output recipe.json

# Save as markdown
recipe-clipper clip-webpage https://example.com/recipe --format markdown --output recipe.md
```

#### Extract from an image

```bash
# Requires ANTHROPIC_API_KEY environment variable
export ANTHROPIC_API_KEY=your-api-key

recipe-clipper clip-image cookbook-photo.jpg

# Save as JSON
recipe-clipper clip-image recipe-card.png --format json --output recipe.json
```

#### Extract from a document

```bash
# Supports PDF, DOCX, TXT, MD
recipe-clipper clip-document recipe.pdf

# With custom model
recipe-clipper clip-document cookbook.docx --model claude-opus-4 --format markdown
```

### Library Usage

#### Extract from a website

```python
from recipe_clipper import clip_recipe

# Without LLM fallback (uses recipe-scrapers only)
recipe = clip_recipe(
    url="https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/",
    api_key=None,
    use_llm_fallback=False
)

print(recipe.title)
for ingredient in recipe.ingredients:
    print(f"- {ingredient.name}")
```

#### With LLM fallback

```python
import os
from recipe_clipper import clip_recipe

api_key = os.getenv("ANTHROPIC_API_KEY")

# Automatically falls back to Claude if recipe-scrapers doesn't support the site
recipe = clip_recipe(
    url="https://unsupported-site.com/recipe",
    api_key=api_key,
    use_llm_fallback=True
)
```

#### Extract from an image

```python
import os
from recipe_clipper.parsers.llm_parser import parse_recipe_from_image

api_key = os.getenv("ANTHROPIC_API_KEY")

recipe = parse_recipe_from_image(
    image_path="cookbook-photo.jpg",
    api_key=api_key,
    model="claude-sonnet-4-5"
)

print(recipe.title)
print(f"Servings: {recipe.metadata.servings}")
```

#### Extract from a document

```python
import os
from recipe_clipper.parsers.llm_parser import parse_recipe_from_document

api_key = os.getenv("ANTHROPIC_API_KEY")

# Supports .pdf, .docx, .txt, .md
recipe = parse_recipe_from_document(
    document_path="recipe.pdf",
    api_key=api_key
)
```

#### Format output

```python
from recipe_clipper import clip_recipe
from recipe_clipper.formatters import (
    format_recipe_text,
    format_recipe_json,
    format_recipe_markdown
)

recipe = clip_recipe("https://example.com/recipe", use_llm_fallback=False)

# Plain text
print(format_recipe_text(recipe))

# JSON
json_str = format_recipe_json(recipe)

# Markdown
markdown_str = format_recipe_markdown(recipe)
```

## Configuration

### API Keys

For Claude features (image/document parsing, website fallback), set your API key:

```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

Or create a `.env` file:

```env
ANTHROPIC_API_KEY=your-api-key-here
```

### Supported Models

- `claude-sonnet-4-5` (default, recommended)
- `claude-sonnet-4`
- `claude-opus-4`
- `claude-3-5-sonnet-20241022`
- `claude-3-5-sonnet-20240620`

## Recipe Data Model

Extracted recipes use a structured Pydantic model:

```python
class Recipe:
    title: str
    ingredients: list[Ingredient]
    instructions: list[str]
    source_url: Optional[AnyUrl]
    image: Optional[HttpUrl]
    metadata: Optional[RecipeMetadata]

class Ingredient:
    name: str
    amount: Optional[str]
    unit: Optional[str]
    preparation: Optional[str]
    display_text: Optional[str]

class RecipeMetadata:
    author: Optional[str]
    servings: Optional[str]
    prep_time: Optional[int]  # minutes
    cook_time: Optional[int]  # minutes
    total_time: Optional[int]  # minutes
    categories: Optional[list[str]]
```

## Supported Input Sources

### 1. Websites (100+ sites)

Uses [recipe-scrapers](https://github.com/hhursev/recipe-scrapers) which supports:
- AllRecipes
- Food Network
- Serious Eats
- NYT Cooking
- And 100+ more sites

For unsupported sites, enable LLM fallback.

### 2. Images

Extracts recipes from:
- Cookbook photos
- Handwritten recipe cards
- Screenshots
- Scanned documents

Supported formats: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`

### 3. Documents

Extracts recipes from:
- PDFs (recipe PDFs, cookbook PDFs)
- Word documents (`.docx`)
- Text files (`.txt`)
- Markdown files (`.md`)

## Development

### Run tests

```bash
# Unit tests only
pytest

# Include integration tests (requires ANTHROPIC_API_KEY)
pytest -m integration
```

### Run linting

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Credits

- Built with [recipe-scrapers](https://github.com/hhursev/recipe-scrapers)
- LLM parsing powered by [Anthropic Claude](https://www.anthropic.com/)
