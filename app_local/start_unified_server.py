#!/usr/bin/env python3
"""
Unified Media Server Launcher
Start the unified server with all media conversion services
"""

import os
import sys
import subprocess

def main():
    # Change to app_local directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("🚀 Starting Unified Media Server...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"📁 Upload folder: {os.path.join(os.getcwd(), 'temp_uploads')}")
    print(f"📁 WebP output folder: {os.path.join(os.getcwd(), 'videos/output')}")
    print(f"📁 Transcode output folder: {os.path.join(os.getcwd(), 'transcode_output')}")
    print("🌐 Server will be available at: http://localhost:5001")
    print("🎨 WebP Converter: http://localhost:5001/webp")
    print("🎬 Media Transcode: http://localhost:5001/transcode")
    print("👁️  WebP Viewer: http://localhost:5001/viewer")
    print("-" * 60)
    
    # Start the server
    try:
        subprocess.run([sys.executable, 'unified_media_server.py'], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())