#!/usr/bin/env python3
"""
Script to check database schema and verify all columns exist
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_schema():
    """Check database schema"""
    
    # Create engine
    engine = create_async_engine(settings.database_url, echo=False)
    
    # Create async session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Check transcode_tasks table columns
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'transcode_tasks' 
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            
            logger.info("📋 transcode_tasks table columns:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
                
            # Check for required columns
            required_columns = [
                'task_id', 'source_url', 'config', 'status', 'created_at', 
                'callback_url', 'callback_auth', 'pubsub_topic',
                'face_detection_status', 'face_detection_results', 'face_detection_error'
            ]
            
            existing_columns = [col[0] for col in columns]
            
            logger.info("\n✅ Column check:")
            for col in required_columns:
                if col in existing_columns:
                    logger.info(f"  ✅ {col} - exists")
                else:
                    logger.error(f"  ❌ {col} - missing")
                    
        except Exception as e:
            logger.error(f"❌ Error checking schema: {e}")
            raise
        finally:
            await session.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_schema())