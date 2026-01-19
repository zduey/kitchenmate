"""KitchenMate API - Recipe extraction service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from kitchen_mate.config import get_settings
from kitchen_mate.db import init_db
from kitchen_mate.routes import auth, clip, convert, me


# Get settings at module load for CORS configuration
# (middleware must be configured before app startup)
_startup_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize resources on startup."""
    # Get settings at startup (allows dependency injection override for tests)
    settings = get_settings()

    if settings.cache_enabled:
        init_db(settings.cache_db_path)
    yield


app = FastAPI(
    title="KitchenMate API",
    description="Recipe extraction API powered by recipe-clipper",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS to allow frontend to send cookies
# Origins can be comma-separated (e.g., "http://localhost:5173,https://example.com")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _startup_settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(clip.router, prefix="/api")
app.include_router(convert.router, prefix="/api")
app.include_router(me.router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Serve frontend static files in production
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Serve static assets (JS, CSS, etc.)
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/")
    async def serve_frontend() -> FileResponse:
        """Serve the frontend application."""
        return FileResponse(frontend_dist / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve the frontend for all non-API routes (SPA routing)."""
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


def run() -> None:
    """Run the application server."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
