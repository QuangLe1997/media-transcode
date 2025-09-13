import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from ..config import settings

logger = logging.getLogger(__name__)

database_url = settings.database_url
logger.info(f"Using database: {database_url.split('@')[0] if '@' in database_url else 'local'}")

# Configure engine based on database type
if "postgresql" in database_url:
    # PostgreSQL configuration with optimized pooling
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_size=5,  # Smaller pool for single worker
        max_overflow=10,  # Reduced overflow
        pool_timeout=10,  # Faster timeout
        pool_recycle=1800,  # 30 minutes
        pool_pre_ping=True,  # Test connections
        pool_reset_on_return="rollback",  # Clean connections
    )
else:
    # SQLite configuration
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=10,
        pool_pre_ping=True,
    )

logger.info("Database engine configured")

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Initialize database tables and warm up connections"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Warm up connection pool
    try:
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            await session.commit()
        logger.info("Database initialized and connection pool warmed up")
    except Exception as e:
        logger.error(f"Database warmup failed: {e}")


async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
