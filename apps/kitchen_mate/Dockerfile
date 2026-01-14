# Stage 1: Build frontend
FROM node:24-slim AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY apps/kitchen_mate/frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY apps/kitchen_mate/frontend/ ./

# Build frontend
RUN npm run build

# Stage 2: Python application
FROM python:3.14-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy recipe-clipper library (path matches pyproject.toml: ../../packages/recipe_clipper)
COPY packages/recipe_clipper/ packages/recipe_clipper/

# Copy app files (maintain directory structure for relative path resolution)
COPY apps/kitchen_mate/ apps/kitchen_mate/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist apps/kitchen_mate/frontend/dist

# Set working directory to app
WORKDIR /app/apps/kitchen_mate

# Install dependencies
RUN uv sync --frozen

# Default port (Render sets PORT environment variable)
ENV PORT=8000
EXPOSE $PORT

# Run the application (shell form to expand $PORT)
CMD uv run uvicorn kitchen_mate.main:app --host 0.0.0.0 --port $PORT
