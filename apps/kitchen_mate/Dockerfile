# Stage 1: Build frontend
FROM node:24-slim AS frontend-builder

WORKDIR /app/frontend

# Accept Supabase environment variables as build arguments
# These are required for multi-tenant mode (Supabase auth)
ARG SUPABASE_URL
ARG SUPABASE_ANON_KEY

# Set as environment variables so Vite can access them during build
ENV SUPABASE_URL=${SUPABASE_URL}
ENV SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}

# Copy frontend package files
COPY apps/kitchen_mate/frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY apps/kitchen_mate/frontend/ ./

# Build frontend (Vite will embed SUPABASE_* env vars into the bundle)
RUN npm run build

# Stage 2: Python application
FROM python:3.14-slim

WORKDIR /app

# Install system dependencies for WeasyPrint (PDF export) and Pillow (image processing)
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy workspace configuration (required for uv to resolve workspace members)
COPY pyproject.toml uv.lock ./

# Copy recipe-clipper library (workspace member)
COPY packages/recipe_clipper/ packages/recipe_clipper/

# Copy app files (workspace member)
COPY apps/kitchen_mate/ apps/kitchen_mate/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/frontend/dist apps/kitchen_mate/frontend/dist

# Set working directory to app
WORKDIR /app/apps/kitchen_mate

# Install dependencies (includes recipe-clipper[llm-anthropic,export] from pyproject.toml)
RUN uv sync --frozen --no-dev

# Default port (Render sets PORT environment variable)
ENV PORT=8000
EXPOSE $PORT

# Run the application (shell form to expand $PORT)
CMD uv run uvicorn kitchen_mate.main:app --host 0.0.0.0 --port $PORT
