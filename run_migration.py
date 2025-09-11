#!/usr/bin/env python3
"""
Simple migration script to add face detection columns
"""

import asyncio
import asyncpg
import sys
import os

async def migrate_database():
    """Add face detection columns to transcode_tasks table"""
    
    # Get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL', 'postgresql://transcode_user:transcode_pass@192.168.0.234:5433/transcode_db')
    
    # Convert asyncpg URL to standard psycopg2 format
    db_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print(f"Connecting to: {db_url}")
    
    try:
        conn = await asyncpg.connect(db_url)
        
        print("Adding face detection columns...")
        
        # Add face detection columns
        await conn.execute("""
            ALTER TABLE transcode_tasks 
            ADD COLUMN IF NOT EXISTS face_detection_status VARCHAR
        """)
        
        await conn.execute("""
            ALTER TABLE transcode_tasks 
            ADD COLUMN IF NOT EXISTS face_detection_results JSON
        """)
        
        await conn.execute("""
            ALTER TABLE transcode_tasks 
            ADD COLUMN IF NOT EXISTS face_detection_error TEXT
        """)
        
        # Create index on face_detection_status
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcode_tasks_face_detection_status 
            ON transcode_tasks(face_detection_status)
        """)
        
        print("✅ Face detection columns added successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_database())