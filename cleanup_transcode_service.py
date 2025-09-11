#!/usr/bin/env python3
"""
Cleanup transcode-service folder
Quick script to remove old transcode-service folder structure
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from s3_deep_clean import S3DeepCleaner

def main():
    print("🧹 Transcode Service Cleanup")
    print("=" * 50)
    
    # Check both possible folder locations
    possible_folders = [
        "dev-facefusion-media/transcode-service",
        "transcode-service"
    ]
    
    cleaner = S3DeepCleaner()
    
    for folder in possible_folders:
        print(f"\n🔍 Checking folder: {folder}")
        
        # Check if folder exists and has content
        objects = cleaner.list_folder_contents(folder + "/", max_items=10)
        
        if objects:
            print(f"✅ Found {len(objects)} objects in {folder}/")
            
            # Ask user if they want to clean this folder
            response = input(f"Do you want to clean {folder}/? (yes/no): ").strip().lower()
            
            if response == 'yes':
                # First show preview
                print(f"\n🔍 Preview of {folder}/:")
                cleaner.deep_clean_folder(folder + "/", dry_run=True)
                
                # Ask for confirmation to proceed
                response = input(f"\nProceed with deletion of {folder}/? (yes/no): ").strip().lower()
                
                if response == 'yes':
                    success = cleaner.deep_clean_folder(folder + "/", dry_run=False)
                    if success:
                        print(f"✅ Successfully cleaned {folder}/")
                    else:
                        print(f"❌ Failed to clean {folder}/")
                else:
                    print(f"⏭️  Skipping {folder}/")
            else:
                print(f"⏭️  Skipping {folder}/")
        else:
            print(f"✅ No objects found in {folder}/ (already clean)")
    
    print("\n🎉 Cleanup process completed!")

if __name__ == "__main__":
    main()