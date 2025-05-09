#!/usr/bin/env python3
"""
Initialize database tables for the Media Transcode Service.
"""
import os
import sqlite3
from config import get_config


def init_db():
    """Initialize the database with tables."""
    print("Initializing database...")

    # Get database path from config
    config = get_config()
    db_path = config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')

    # Make sure the directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Check if script file exists
    schema_path = os.path.join('database', 'schema.sql')
    if not os.path.exists(schema_path):
        print(f"Error: Schema file not found: {schema_path}")
        return False

    # Read SQL schema
    with open(schema_path, 'r') as f:
        sql_script = f.read()

    # Connect to database and execute schema
    try:
        conn = sqlite3.connect(db_path)
        conn.executescript(sql_script)
        conn.commit()
        conn.close()
        print(f"Database initialized successfully: {db_path}")
        return True
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return False


if __name__ == "__main__":
    init_db()