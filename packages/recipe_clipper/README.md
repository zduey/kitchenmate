# Recipe Clipper

[![Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://www.python.org/downloads/)
[![codecov](https://codecov.io/gh/zduey/recipe-clipper/branch/master/graph/badge.svg)](https://codecov.io/gh/zduey/recipe-clipper)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://img.shields.io/pypi/v/recipe-clipper.svg)](https://pypi.org/project/recipe-clipper/)

Extract recipes from websites, images, and documents with ease. Recipe Clipper supports multiple input sources and uses both web scraping and LLMs to extract structured recipe data from documents and images.

## Installation

### Basic Installation

```bash
pip install recipe-clipper
```
### With LLM-fallback support using Claude

```bash
pip install recipe-clipper[llm]
```

## Quick Start

### CLI Usage

#### Extract from a website

```bash
# Basic usage, outputs recipe as text file
recipe-clipper clip-webpage https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/

# Use a different output format
recipe-clipper clip-webpage https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/ --format json --output chocolate_chip_cookies.json

# Use LLM fallback for recipes that are not supported by recipe-scrapers
export ANTROPIC_API_KEY=your-api-key
recipe-clipper clip-webpage https://smittenkitchen.com/2011/02/meatball-sub-with-caramelized-onions/ --use-llm-fallback

```

#### Extract from an image

```bash
# Requires ANTHROPIC_API_KEY environment variable
export ANTHROPIC_API_KEY=your-api-key

# Supports jpg, jpeg, png, gif, webp
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
recipe = clip_recipe(url="https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/")
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
    url="https://smittenkitchen.com/2011/02/meatball-sub-with-caramelized-onions/",
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

recipe = clip_recipe("https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/")

# Plain text
print(format_recipe_text(recipe))

# JSON
json_str = format_recipe_json(recipe)
print(json_str)

# Markdown
markdown_str = format_recipe_markdown(recipe)
print(markdown_str)
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
