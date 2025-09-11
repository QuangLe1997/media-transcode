#!/usr/bin/env python3
"""
Quick clean delete markers - Fast removal of S3 delete markers
"""

import os
import sys
import boto3
from pathlib import Path
from botocore.exceptions import ClientError

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from config import settings

def quick_clean_delete_markers(folder_prefix: str):
    """Quickly clean delete markers from a folder"""
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name='us-east-1'
        )
        
        bucket_name = settings.aws_bucket_name
        
        # Ensure folder prefix ends with /
        if not folder_prefix.endswith('/'):
            folder_prefix += '/'
        
        print(f"🗑️  Quick cleaning delete markers in: {folder_prefix}")
        
        deleted_count = 0
        batch_count = 0
        
        try:
            paginator = s3_client.get_paginator('list_object_versions')
            
            for page in paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix):
                if 'DeleteMarkers' in page and page['DeleteMarkers']:
                    delete_markers = page['DeleteMarkers']
                    
                    # Process in batches of 1000
                    for i in range(0, len(delete_markers), 1000):
                        batch = delete_markers[i:i + 1000]
                        batch_count += 1
                        
                        try:
                            delete_request = {
                                'Objects': [
                                    {'Key': marker['Key'], 'VersionId': marker['VersionId']} 
                                    for marker in batch
                                ]
                            }
                            
                            response = s3_client.delete_objects(
                                Bucket=bucket_name,
                                Delete=delete_request
                            )
                            
                            batch_deleted = len(response.get('Deleted', []))
                            deleted_count += batch_deleted
                            
                            print(f"✅ Batch {batch_count}: removed {batch_deleted} delete markers")
                            
                        except ClientError as e:
                            print(f"❌ Batch {batch_count} failed: {e}")
        
        except ClientError as e:
            print(f"❌ Error: {e}")
            return False
        
        print(f"\n🎉 Completed!")
        print(f"✅ Total delete markers removed: {deleted_count}")
        
        if deleted_count > 0:
            print(f"💡 Folder {folder_prefix} should now be completely clean")
            print(f"🔄 Refresh your S3 console to see the folder disappear")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Quick clean S3 delete markers')
    parser.add_argument('--folder', required=True, help='Folder prefix to clean')
    
    args = parser.parse_args()
    
    success = quick_clean_delete_markers(args.folder)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()