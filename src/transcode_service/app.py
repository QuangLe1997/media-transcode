#!/usr/bin/env python3

"""
Main application entry point for Transcode Service
Serves only the FastAPI application from main.py
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Main entry point - runs FastAPI with uvicorn"""
    import uvicorn

    # Import the FastAPI app from main.py

    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', '8087'))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'

    print(f"🚀 Starting Transcode Service API on {host}:{port}")
    print(f"📍 API endpoints available at: http://{host}:{port}")
    print(f"🔧 Debug mode: {debug}")

    # Run FastAPI with uvicorn
    uvicorn.run(
        "transcode_service.api.main:app",
        host=host,
        port=port,
        log_level="debug" if debug else "info",
        reload=debug,
        access_log=True
    )


if __name__ == '__main__':
    main()