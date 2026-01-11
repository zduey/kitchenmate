# Kitchen Mate

Full-stack recipe extraction application with a React frontend and FastAPI backend, powered by the `recipe-clipper` library.

## Features

- **Web Interface**: Clean, responsive React UI for extracting recipes
- **REST API**: Extract recipes from URLs via HTTP API
- **Multiple Formats**: JSON, plain text, and markdown output
- **Download Support**: Save recipes as files directly from the UI
- **LLM Fallback**: Support for unsupported websites (requires Anthropic API key)
- **Docker Deployment**: Single container with frontend and backend

## Frontend

The React frontend provides a user-friendly interface for recipe extraction.

### Technology Stack

- **React 18** with TypeScript
- **Vite** for fast development and builds
- **Tailwind CSS** for styling

### Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server (port 5173)
npm run dev

# Build for production
npm run build

# Run linting
npm run lint
```

The Vite dev server proxies `/clip` and `/health` requests to the backend at `http://localhost:8000`.

## Backend

The FastAPI backend provides the REST API for recipe extraction.

#### Health Check

```
GET /health
```

Returns `{"status": "healthy"}` when the service is running.

#### Extract Recipe

```
POST /clip
```

**Request Body:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | string | required | URL of the recipe page |
| `format` | string | `"json"` | Output format: `"json"`, `"text"`, or `"markdown"` |
| `timeout` | integer | `10` | HTTP timeout in seconds (1-60) |
| `use_llm_fallback` | boolean | `false` | Enable LLM parsing for unsupported sites |
| `download` | boolean | `false` | Return response as file download |

**Example Request:**

```bash
curl -X POST http://localhost:8000/clip \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/"}'
```

**Example Response (JSON format):**

```json
{
  "title": "Best Chocolate Chip Cookies",
  "ingredients": [
    {"name": "1 cup butter, softened"},
    {"name": "1 cup white sugar"}
  ],
  "instructions": [
    "Preheat the oven to 350 degrees F.",
    "Beat butter and sugar until smooth."
  ],
  "source_url": "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/",
  "image": "https://...",
  "metadata": {
    "author": "Dora",
    "servings": "48 servings",
    "prep_time": 20,
    "cook_time": 10,
    "total_time": 30
  }
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid request (e.g., LLM fallback without API key) |
| 404 | Recipe not found on unsupported site |
| 422 | Invalid request body |
| 502 | Failed to fetch the source URL |
| 500 | Internal parsing error |

## Development

### Full Stack Development

To run the complete application locally:

```bash
# Terminal 1: Start the backend (port 8000)
uv run uvicorn kitchen_mate.main:app --reload

# Terminal 2: Start the frontend (port 5173)
cd frontend && npm run dev
```

Open http://localhost:5173 to use the application.

### Backend Only

```bash
# Install dependencies
uv sync --extra dev

# Run development server
uv run uvicorn kitchen_mate.main:app --reload
```

### Testing

```bash
# Backend tests
uv run pytest -v
```

### Linting

```bash
# Backend
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Frontend
cd frontend && npm run lint
```

## Docker

The application uses a multi-stage Docker build that compiles the frontend and bundles it with the backend into a single container.

### Build and Run

```bash
# From repository root
docker compose up --build
```

The application will be available at http://localhost:8000.

### Image Details

- **Base images**: `node:24-slim` (build), `python:3.14-slim` (runtime)
- **Multi-stage build**: Frontend built separately, assets copied to final image
- **Static serving**: FastAPI serves the React SPA and handles client-side routing

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | API key for LLM fallback (optional) |

### GitHub Container Registry

Docker images are automatically built and pushed to GHCR on pushes to main:

```bash
docker pull ghcr.io/zduey/ktichenmate:latest
```

## Dependencies

### Backend

- **FastAPI**: Web framework
- **uvicorn**: ASGI server
- **pydantic-settings**: Configuration management
- **recipe-clipper**: Recipe extraction library

### Frontend

- **React 18**: UI framework
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool
- **Tailwind CSS**: Utility-first CSS
