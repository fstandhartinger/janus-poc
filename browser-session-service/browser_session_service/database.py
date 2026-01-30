"""Database connection and session management."""

from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from browser_session_service.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


# Lazy-initialized database components
_engine: Optional[AsyncEngine] = None
_session_local: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine (lazy initialization)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the session maker (lazy initialization)."""
    global _session_local
    if _session_local is None:
        _session_local = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_local


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


async def init_db() -> None:
    """Initialize database tables."""
    import browser_session_service.schemas  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_local
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_local = None
