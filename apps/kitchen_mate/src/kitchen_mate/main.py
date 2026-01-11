"""KitchenMate API - Recipe extraction service."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from kitchen_mate.routes import clip

app = FastAPI(
    title="KitchenMate API",
    description="Recipe extraction API powered by recipe-clipper",
    version="0.1.0",
)

app.include_router(clip.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


def run() -> None:
    """Run the application server."""
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
