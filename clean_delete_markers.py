#!/usr/bin/env python3
"""
Clean S3 delete markers - Remove lingering delete markers that keep folders visible
"""

import os
import sys
import boto3
import logging
from pathlib import Path
from botocore.exceptions import ClientError

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from config import settings

def clean_delete_markers(folder_prefix: str):
    """Clean delete markers from a folder"""
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
        
        print(f"🔍 Scanning for delete markers in: {folder_prefix}")
        print(f"📁 Bucket: {bucket_name}")
        
        # Collect all delete markers
        delete_markers = []
        
        try:
            paginator = s3_client.get_paginator('list_object_versions')
            
            for page in paginator.paginate(Bucket=bucket_name, Prefix=folder_prefix):
                if 'DeleteMarkers' in page:
                    for marker in page['DeleteMarkers']:
                        delete_markers.append({
                            'Key': marker['Key'],
                            'VersionId': marker['VersionId']
                        })
        
        except ClientError as e:
            print(f"❌ Error listing delete markers: {e}")
            return False
        
        if not delete_markers:
            print(f"✅ No delete markers found in {folder_prefix}")
            return True
        
        print(f"🗑️  Found {len(delete_markers)} delete markers to remove")
        
        # Show some examples
        print("📋 Examples:")
        for marker in delete_markers[:5]:
            print(f"   - {marker['Key']}")
        if len(delete_markers) > 5:
            print(f"   ... and {len(delete_markers) - 5} more")
        
        # Auto-confirm for large numbers
        if len(delete_markers) > 1000:
            print(f"\n🚨 Auto-confirming removal of {len(delete_markers)} delete markers...")
            print("💡 This will clean up the folder completely")
        else:
            response = input(f"\n🚨 Remove all {len(delete_markers)} delete markers? (yes/no): ").strip().lower()
            
            if response != 'yes':
                print("❌ Operation cancelled")
                return False
        
        # Delete markers in batches
        print(f"\n🗑️  Removing {len(delete_markers)} delete markers...")
        
        deleted_count = 0
        failed_count = 0
        
        # Process in batches of 1000
        for i in range(0, len(delete_markers), 1000):
            batch = delete_markers[i:i + 1000]
            
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
                
                if 'Errors' in response:
                    for error in response['Errors']:
                        failed_count += 1
                        print(f"❌ Failed to delete {error['Key']}: {error['Message']}")
                
                print(f"✅ Batch {i//1000 + 1}: removed {batch_deleted} delete markers")
                
            except ClientError as e:
                failed_count += len(batch)
                print(f"❌ Batch {i//1000 + 1} failed: {e}")
        
        # Summary
        print(f"\n📊 Results:")
        print(f"✅ Successfully removed: {deleted_count} delete markers")
        if failed_count > 0:
            print(f"❌ Failed to remove: {failed_count} delete markers")
        
        # Verify folder is now clean
        print(f"\n🔍 Verifying folder is clean...")
        
        # Quick check
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=folder_prefix,
            MaxKeys=1
        )
        
        if 'Contents' in response:
            print(f"⚠️  Folder still contains regular objects")
            return False
        
        # Check delete markers again
        response = s3_client.list_object_versions(
            Bucket=bucket_name,
            Prefix=folder_prefix,
            MaxKeys=1
        )
        
        if 'DeleteMarkers' in response and response['DeleteMarkers']:
            print(f"⚠️  Some delete markers still remain")
            return False
        
        print(f"🎉 Folder {folder_prefix} is now completely clean!")
        print(f"💡 Refresh your S3 console - the folder should disappear")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean S3 delete markers')
    parser.add_argument('--folder', required=True, help='Folder prefix to clean')
    
    args = parser.parse_args()
    
    success = clean_delete_markers(args.folder)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()