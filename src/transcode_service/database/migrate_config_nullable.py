#!/usr/bin/env python3
"""
Migration script to make Job.config_id nullable and add SET NULL on delete
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Migrate the database to make config_id nullable"""
    
    # Database path
    db_path = Path(__file__).parent.parent / 'instance' / 'media_transcode.db'
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    print(f"Migrating database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        print("Current jobs table schema:")
        for col in columns:
            print(f"  {col}")
        
        # SQLite doesn't support ALTER COLUMN directly, so we need to recreate table
        print("\nCreating backup of jobs table...")
        cursor.execute("""
            CREATE TABLE jobs_backup AS 
            SELECT * FROM jobs
        """)
        
        print("Dropping original jobs table...")
        cursor.execute("DROP TABLE jobs")
        
        print("Creating new jobs table with nullable config_id...")
        cursor.execute("""
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                config_id INTEGER,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (config_id) REFERENCES configs (id) ON DELETE SET NULL
            )
        """)
        
        print("Restoring data from backup...")
        cursor.execute("""
            INSERT INTO jobs (id, user_id, config_id, status, created_at, updated_at)
            SELECT id, user_id, config_id, status, created_at, updated_at 
            FROM jobs_backup
        """)
        
        print("Dropping backup table...")
        cursor.execute("DROP TABLE jobs_backup")
        
        # Commit changes
        conn.commit()
        
        # Verify new schema
        cursor.execute("PRAGMA table_info(jobs)")
        columns = cursor.fetchall()
        print("\nNew jobs table schema:")
        for col in columns:
            print(f"  {col}")
        
        # Check foreign keys
        cursor.execute("PRAGMA foreign_key_list(jobs)")
        fkeys = cursor.fetchall()
        print("\nForeign keys:")
        for fkey in fkeys:
            print(f"  {fkey}")
        
        print("\nMigration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()