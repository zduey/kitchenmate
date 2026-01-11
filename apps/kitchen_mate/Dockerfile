FROM python:3.14-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy recipe-clipper library (path matches pyproject.toml: ../../packages/recipe_clipper)
COPY packages/recipe_clipper/ packages/recipe_clipper/

# Copy app files (maintain directory structure for relative path resolution)
COPY apps/kitchen_mate/ apps/kitchen_mate/

# Set working directory to app
WORKDIR /app/apps/kitchen_mate

# Install dependencies
RUN uv sync --frozen

# Expose the default port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "kitchen_mate.main:app", "--host", "0.0.0.0", "--port", "8000"]
