from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import settings

engine = create_async_engine(
    settings.database_url_parsed,

    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    future=True,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        yield session
