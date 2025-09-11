#!/usr/bin/env python3
"""
Check S3 folder status - see if folder is truly empty
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

def check_folder_status(folder_prefix: str):
    """Check if folder is truly empty"""
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
        
        print(f"🔍 Checking folder: {folder_prefix}")
        print(f"📁 Bucket: {bucket_name}")
        
        # Check regular objects
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=folder_prefix,
            MaxKeys=10
        )
        
        objects = response.get('Contents', [])
        
        if objects:
            print(f"❌ Folder still contains {len(objects)} objects:")
            for obj in objects[:5]:
                print(f"   - {obj['Key']} ({obj['Size']} bytes)")
            if len(objects) > 5:
                print(f"   ... and {len(objects) - 5} more objects")
        else:
            print(f"✅ No regular objects found in {folder_prefix}")
        
        # Check multipart uploads
        try:
            response = s3_client.list_multipart_uploads(
                Bucket=bucket_name,
                Prefix=folder_prefix,
                MaxUploads=10
            )
            
            uploads = response.get('Uploads', [])
            
            if uploads:
                print(f"⚠️  Found {len(uploads)} incomplete multipart uploads:")
                for upload in uploads[:5]:
                    print(f"   - {upload['Key']} (Upload ID: {upload['UploadId']})")
                if len(uploads) > 5:
                    print(f"   ... and {len(uploads) - 5} more uploads")
            else:
                print(f"✅ No multipart uploads found in {folder_prefix}")
        except ClientError as e:
            print(f"⚠️  Could not check multipart uploads: {e}")
        
        # Check object versions
        try:
            response = s3_client.list_object_versions(
                Bucket=bucket_name,
                Prefix=folder_prefix,
                MaxKeys=10
            )
            
            versions = response.get('Versions', [])
            delete_markers = response.get('DeleteMarkers', [])
            
            if versions:
                print(f"⚠️  Found {len(versions)} object versions:")
                for version in versions[:5]:
                    print(f"   - {version['Key']} (Version: {version['VersionId']})")
                if len(versions) > 5:
                    print(f"   ... and {len(versions) - 5} more versions")
            else:
                print(f"✅ No object versions found in {folder_prefix}")
            
            if delete_markers:
                print(f"⚠️  Found {len(delete_markers)} delete markers:")
                for marker in delete_markers[:5]:
                    print(f"   - {marker['Key']} (Version: {marker['VersionId']})")
                if len(delete_markers) > 5:
                    print(f"   ... and {len(delete_markers) - 5} more markers")
            else:
                print(f"✅ No delete markers found in {folder_prefix}")
        except ClientError as e:
            print(f"⚠️  Could not check object versions: {e}")
        
        # Summary
        total_items = len(objects) + len(uploads) + len(versions) + len(delete_markers)
        
        if total_items == 0:
            print(f"\n🎉 Folder {folder_prefix} is completely empty!")
            print(f"💡 If you still see it in S3 console, try refreshing or it may be cached")
        else:
            print(f"\n⚠️  Folder {folder_prefix} still contains {total_items} items")
            print(f"🧹 Use the deep folder clean script to remove remaining items")
        
    except Exception as e:
        print(f"❌ Error checking folder: {e}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check S3 folder status')
    parser.add_argument('--folder', required=True, help='Folder prefix to check')
    
    args = parser.parse_args()
    
    check_folder_status(args.folder)

if __name__ == "__main__":
    main()