# Recipe Clipper

Extract recipes from websites with ease.

## Installation

```bash
pip install recipe-clipper
```

### Optional LLM Support

For LLM-based fallback parsing when recipe-scrapers doesn't support a website:

```bash
# Anthropic Claude
pip install recipe-clipper[llm-anthropic]

# OpenAI GPT
pip install recipe-clipper[llm-openai]

# Google Gemini
pip install recipe-clipper[llm-google]

# Cohere
pip install recipe-clipper[llm-cohere]

# All LLM providers
pip install recipe-clipper[llm]
```

## Features

- Extracts recipes from 100+ websites using [recipe-scrapers](https://github.com/hhursev/recipe-scrapers)
- Optional LLM fallback for unsupported websites
- Both synchronous and asynchronous APIs
- CLI tool for quick recipe extraction
- Type-safe with full type hints
- Immutable data models using Pydantic

## License

MIT
