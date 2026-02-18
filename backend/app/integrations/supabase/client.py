from functools import lru_cache

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


@lru_cache
def _get_engine():
    settings = get_settings()
    # Supabase pooler (Supavisor) uses transaction mode which doesn't support
    # prepared statements. Disable statement_cache_size and use NullPool since
    # Supavisor handles connection pooling server-side.
    is_pooler = "pooler.supabase.com" in settings.database_url
    connect_args = {"statement_cache_size": 0} if is_pooler else {}
    return create_async_engine(
        settings.database_url,
        echo=settings.is_development,
        pool_pre_ping=True,
        connect_args=connect_args,
        **({"poolclass": pool.NullPool} if is_pooler else {"pool_size": 5, "max_overflow": 10}),
    )


@lru_cache
def _get_session_factory():
    return async_sessionmaker(
        _get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncSession:
    """Dependency that provides an async database session."""
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
