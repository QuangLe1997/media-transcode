#!/usr/bin/env python3
"""
Migration script to create config_templates table
"""

import asyncio
import asyncpg
import sys
import os

async def create_table():
    """Create config_templates table"""
    
    # Get DATABASE_URL from environment
    database_url = os.getenv('DATABASE_URL', 'postgresql://transcode_user:transcode_pass@192.168.0.234:5433/transcode_db')
    
    # Convert asyncpg URL to standard psycopg2 format
    db_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print(f"Connecting to: {db_url}")
    
    try:
        conn = await asyncpg.connect(db_url)
        
        print("Creating config_templates table...")
        
        # Create config_templates table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS config_templates (
                template_id VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                config JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # Create index on name for searching
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_config_templates_name 
            ON config_templates(name)
        """)
        
        print("✅ config_templates table created successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_table())