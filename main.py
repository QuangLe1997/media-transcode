#!/usr/bin/env python3
"""
Main entry point for Transcode Service API
Simple server runner
"""

import os
import sys

import uvicorn
from dotenv import load_dotenv

from logging_config import setup_logging

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
load_dotenv()


def main():
    """Main function to run the FastAPI server"""

    # Check if .env file exists
    setup_logging()
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ Loading environment from {env_file}")
    else:
        print(f"⚠️  No .env file found. Using system environment variables.")
        if os.path.exists(".env.template"):
            print(f"   Template available: .env.template")

    # Configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8088"))
    debug = os.getenv("DEBUG", "false").lower() == "true"

    # Show configuration
    print(f"🚀 Starting Transcode API Server")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Debug: {debug}")
    print(f"   Database: {os.getenv('DATABASE_URL', 'Not configured')[:50]}...")
    print()

    # Run the server
    try:
        print("🔄 Starting uvicorn server...")

        # Try different ASGI servers
        server_type = os.getenv("ASGI_SERVER", "uvicorn").lower()

        if server_type == "hypercorn":
            # Use Hypercorn
            import subprocess
            subprocess.run([
                "hypercorn",
                "api.main:app",
                "--bind", f"{host}:{port}"
            ])
        elif server_type == "gunicorn":
            # Use Gunicorn with uvicorn workers
            import subprocess
            subprocess.run([
                "gunicorn",
                "api.main:app",
                "-w", "2",  # 2 workers
                "-k", "uvicorn.workers.UvicornWorker",
                "--bind", f"{host}:{port}"
            ])
        else:
            # Default: Uvicorn
            from api.main import app
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info"
            )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
