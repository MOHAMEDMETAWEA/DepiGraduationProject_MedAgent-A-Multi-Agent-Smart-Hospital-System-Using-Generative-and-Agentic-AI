from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_engine: AsyncEngine | None = None
_async_session_local: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    """Phase E (E7): all pool sizing is driven by config so ops can tune in
    prod without code changes. Defaults are conservative for a single backend
    container — bump `DB_POOL_SIZE` when scaling horizontally."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        )
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_local


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _get_session_factory()() as session:
        yield session


def get_session() -> AsyncSession:
    """Return a new async session (caller must close it)."""
    return _get_session_factory()()
