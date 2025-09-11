#!/usr/bin/env python3
"""
Quick S3 Clean - Delete multiple folders with single confirmation
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from s3_bulk_clean import S3BulkCleaner

def main():
    """Quick cleanup of common old folders"""
    
    print("🧹 Quick S3 Cleanup")
    print("=" * 50)
    
    # Common old folder patterns to clean
    folders_to_clean = [
        'dev-facefusion-media/transcode-service',
        'transcode-service',
        'old-transcode-outputs',
        'temp-uploads',
        'test-outputs',
        'face-detection-temp',
        'legacy-outputs'
    ]
    
    cleaner = S3BulkCleaner()
    
    print(f"📁 Will scan these folders:")
    for folder in folders_to_clean:
        print(f"   - {folder}")
    
    print(f"\n🔍 Scanning folders...")
    
    # Perform bulk deletion with single confirmation
    success = cleaner.bulk_delete_folders(folders_to_clean, dry_run=False)
    
    if success:
        print(f"\n🎉 Quick cleanup completed!")
    else:
        print(f"\n❌ Quick cleanup failed or cancelled")

if __name__ == "__main__":
    main()