#!/usr/bin/env python3
"""
Database initialization script for transcode service
"""
import asyncio
import sys
import os

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from transcode_service.core.db.database import init_db, engine
from transcode_service.core.db.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """Create all database tables"""
    logger.info("Creating database tables...")
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully!")


async def main():
    """Main initialization function"""
    try:
        await create_tables()
        await init_db()
        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())