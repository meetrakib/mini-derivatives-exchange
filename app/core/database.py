from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_users_auth_columns()


async def _migrate_users_auth_columns() -> None:
    """Add email and password_hash to users if missing (one-time migration for existing DBs)."""
    from sqlalchemy import text
    async with engine.begin() as conn:
        for column, spec in [
            ("email", "VARCHAR(256)"),
            ("password_hash", "VARCHAR(256)"),
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN {column} {spec}"))
            except Exception:
                pass
        try:
            await conn.execute(text("CREATE UNIQUE INDEX ix_users_email ON users (email)"))
        except Exception:
            pass
