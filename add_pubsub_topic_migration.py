#!/usr/bin/env python3
"""
Migration script to add pubsub_topic column to existing database
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_database():
    """Add pubsub_topic column to transcode_tasks table"""
    
    # Create engine
    engine = create_async_engine(settings.database_url, echo=True)
    
    # Create async session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Check if pubsub_topic column exists
            result = await session.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'transcode_tasks' 
                AND column_name = 'pubsub_topic'
            """))
            
            column_exists = result.scalar() > 0
            
            if not column_exists:
                logger.info("Adding pubsub_topic column to transcode_tasks table...")
                
                # Add pubsub_topic column
                await session.execute(text("""
                    ALTER TABLE transcode_tasks 
                    ADD COLUMN pubsub_topic VARCHAR(255) NULL
                """))
                
                await session.commit()
                logger.info("✅ Successfully added pubsub_topic column")
            else:
                logger.info("✅ pubsub_topic column already exists")
                
        except Exception as e:
            logger.error(f"❌ Error during migration: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_database())