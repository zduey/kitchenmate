"""Async database engine and session management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Module-level state (initialized on startup)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_database(db_path: str) -> None:
    """Initialize the async database engine and session factory.

    Args:
        db_path: Path to the SQLite database file
    """
    global _engine, _session_factory

    # Create parent directory if needed
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # aiosqlite connection string format
    database_url = f"sqlite+aiosqlite:///{db_path}"

    _engine = create_async_engine(
        database_url,
        echo=False,  # Set True for SQL logging during development
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Prevent lazy loading issues after commit
        autoflush=False,
    )


async def close_database() -> None:
    """Close the database engine."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_engine() -> AsyncEngine:
    """Get the async engine.

    Returns:
        The async engine

    Raises:
        RuntimeError: If database not initialized
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the session factory.

    Returns:
        The async session factory

    Raises:
        RuntimeError: If database not initialized
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session.

    Usage:
        async with get_session() as session:
            result = await session.execute(...)

    The session automatically commits on success and rolls back on exception.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Create all tables in the database.

    This is mainly for testing purposes. In production, use Alembic migrations.
    """
    from kitchen_mate.database.models import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
