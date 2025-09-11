#!/usr/bin/env python3
"""
Migration script to add face detection columns to existing database
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
    """Add face detection columns to transcode_tasks table"""
    
    # Create engine
    engine = create_async_engine(settings.database_url, echo=True)
    
    try:
        async with engine.begin() as conn:
            logger.info("Adding face detection columns...")
            
            # Add face detection columns
            await conn.execute(text("""
                ALTER TABLE transcode_tasks 
                ADD COLUMN IF NOT EXISTS face_detection_status VARCHAR
            """))
            
            await conn.execute(text("""
                ALTER TABLE transcode_tasks 
                ADD COLUMN IF NOT EXISTS face_detection_results JSON
            """))
            
            await conn.execute(text("""
                ALTER TABLE transcode_tasks 
                ADD COLUMN IF NOT EXISTS face_detection_error TEXT
            """))
            
            # Create index on face_detection_status
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_transcode_tasks_face_detection_status 
                ON transcode_tasks(face_detection_status)
            """))
            
            logger.info("✅ Face detection columns added successfully!")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_database())