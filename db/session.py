"""Async engine/session factory. Pooling is handled by SQLAlchemy's QueuePool (asyncpg)."""
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from config import settings


def normalize_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


_engine: AsyncEngine | None = None
_factory: async_sessionmaker[AsyncSession] | None = None


def configure(url: str | None = None) -> AsyncEngine:
    """(Re)build the global engine. Tests call this with their own URL."""
    global _engine, _factory
    url = normalize_url(url or settings.DATABASE_URL)
    kwargs = {"connect_args": {"timeout": 30}} if url.startswith("sqlite") else {"pool_size": 10, "max_overflow": 10, "pool_pre_ping": True}
    _engine = create_async_engine(url, **kwargs)
    _factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_engine() -> AsyncEngine:
    return _engine or configure()


def session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _factory is not None
    return _factory


@asynccontextmanager
async def session_scope():
    """Independent session (use one per concurrent task; sessions are not task-safe)."""
    async with session_factory()() as s:
        yield s


async def get_session():
    """FastAPI dependency."""
    async with session_factory()() as s:
        yield s


async def dispose() -> None:
    global _engine, _factory
    if _engine is not None:
        await _engine.dispose()
    _engine = _factory = None
