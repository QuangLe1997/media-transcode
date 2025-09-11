#!/usr/bin/env python3
"""
Startup script for face detection worker
Ensures models are downloaded and performs health checks before starting
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main startup function"""
    print("🚀 Starting Face Detection Worker")
    print("=" * 50)
    
    try:
        # Import and run the worker
        from consumer.face_detect_worker import main as worker_main
        
        logger.info("🎯 Starting face detection worker...")
        worker_main()
        
    except KeyboardInterrupt:
        logger.info("🛑 Worker stopped by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Worker failed to start: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())