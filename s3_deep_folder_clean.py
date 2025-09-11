#!/usr/bin/env python3
"""
S3 Deep Folder Clean - Remove folders completely including hidden objects
"""

import os
import sys
import boto3
import logging
from pathlib import Path
from typing import List, Dict
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class S3DeepFolderCleaner:
    """Deep clean S3 folders including hidden objects and folder markers"""
    
    def __init__(self):
        """Initialize S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.aws_endpoint_url,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name='us-east-1'
            )
            self.bucket_name = settings.aws_bucket_name
            logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            sys.exit(1)
    
    def list_all_objects(self, folder_prefix: str) -> List[Dict]:
        """List ALL objects including hidden ones and folder markers"""
        try:
            all_objects = []
            progress_counter = 0
            
            # List regular objects
            print("📋 Scanning regular objects...")
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_count = 0
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=folder_prefix):
                page_count += 1
                if 'Contents' in page:
                    for obj in page['Contents']:
                        all_objects.append({
                            'Key': obj['Key'],
                            'Size': obj['Size'],
                            'Type': 'object'
                        })
                        progress_counter += 1
                        if progress_counter % 10000 == 0:
                            print(f"   ⏳ Found {progress_counter:,} objects so far...")
                if page_count % 10 == 0:
                    print(f"   📄 Processed {page_count} pages...")
            
            regular_count = len([o for o in all_objects if o['Type'] == 'object'])
            print(f"   ✅ Found {regular_count:,} regular objects")
            
            # List multipart uploads (incomplete uploads)
            try:
                print("📋 Scanning multipart uploads...")
                multipart_count = 0
                paginator = self.s3_client.get_paginator('list_multipart_uploads')
                for page in paginator.paginate(Bucket=self.bucket_name, Prefix=folder_prefix):
                    if 'Uploads' in page:
                        for upload in page['Uploads']:
                            all_objects.append({
                                'Key': upload['Key'],
                                'UploadId': upload['UploadId'],
                                'Type': 'multipart'
                            })
                            multipart_count += 1
                            if multipart_count % 1000 == 0:
                                print(f"   ⏳ Found {multipart_count:,} multipart uploads...")
                print(f"   ✅ Found {multipart_count:,} multipart uploads")
            except ClientError as e:
                logger.warning(f"Could not list multipart uploads: {e}")
            
            # List object versions (if versioning is enabled)
            try:
                print("📋 Scanning object versions and delete markers...")
                version_count = 0
                marker_count = 0
                page_count = 0
                paginator = self.s3_client.get_paginator('list_object_versions')
                for page in paginator.paginate(Bucket=self.bucket_name, Prefix=folder_prefix):
                    page_count += 1
                    if 'Versions' in page:
                        for version in page['Versions']:
                            # Skip current versions (already handled above)
                            if not version.get('IsLatest', False):
                                all_objects.append({
                                    'Key': version['Key'],
                                    'VersionId': version['VersionId'],
                                    'Type': 'version'
                                })
                                version_count += 1
                    
                    if 'DeleteMarkers' in page:
                        for marker in page['DeleteMarkers']:
                            all_objects.append({
                                'Key': marker['Key'],
                                'VersionId': marker['VersionId'],
                                'Type': 'delete_marker'
                            })
                            marker_count += 1
                    
                    if page_count % 10 == 0:
                        print(f"   📄 Processed {page_count} version pages...")
                        print(f"   ⏳ Versions: {version_count:,}, Delete markers: {marker_count:,}")
                
                print(f"   ✅ Found {version_count:,} object versions")
                print(f"   ✅ Found {marker_count:,} delete markers")
            except ClientError as e:
                logger.warning(f"Could not list object versions: {e}")
            
            return all_objects
            
        except ClientError as e:
            logger.error(f"Error listing objects: {e}")
            return []
    
    def delete_all_objects(self, objects: List[Dict]) -> Dict:
        """Delete all types of objects including hidden ones"""
        results = {
            'objects_deleted': 0,
            'multipart_aborted': 0,
            'versions_deleted': 0,
            'delete_markers_deleted': 0,
            'errors': []
        }
        
        # Group objects by type
        regular_objects = []
        multipart_uploads = []
        versions = []
        delete_markers = []
        
        for obj in objects:
            if obj['Type'] == 'object':
                regular_objects.append(obj)
            elif obj['Type'] == 'multipart':
                multipart_uploads.append(obj)
            elif obj['Type'] == 'version':
                versions.append(obj)
            elif obj['Type'] == 'delete_marker':
                delete_markers.append(obj)
        
        # Delete regular objects
        if regular_objects:
            print(f"🗑️  Deleting {len(regular_objects)} regular objects...")
            try:
                # Batch delete regular objects
                total_batches = (len(regular_objects) + 999) // 1000
                for i in range(0, len(regular_objects), 1000):
                    batch = regular_objects[i:i + 1000]
                    batch_num = i // 1000 + 1
                    
                    delete_request = {
                        'Objects': [{'Key': obj['Key']} for obj in batch]
                    }
                    
                    response = self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete=delete_request
                    )
                    
                    batch_deleted = len(response.get('Deleted', []))
                    results['objects_deleted'] += batch_deleted
                    
                    # Progress logging
                    progress = (batch_num / total_batches) * 100
                    print(f"   📦 Batch {batch_num}/{total_batches} ({progress:.1f}%): deleted {batch_deleted} objects")
                    
                    if 'Errors' in response:
                        for error in response['Errors']:
                            results['errors'].append(f"Object {error['Key']}: {error['Message']}")
                            
            except ClientError as e:
                results['errors'].append(f"Failed to delete regular objects: {e}")
        
        # Abort multipart uploads
        if multipart_uploads:
            print(f"🚫 Aborting {len(multipart_uploads)} multipart uploads...")
            for upload in multipart_uploads:
                try:
                    self.s3_client.abort_multipart_upload(
                        Bucket=self.bucket_name,
                        Key=upload['Key'],
                        UploadId=upload['UploadId']
                    )
                    results['multipart_aborted'] += 1
                except ClientError as e:
                    results['errors'].append(f"Failed to abort multipart {upload['Key']}: {e}")
        
        # Delete object versions
        if versions:
            print(f"🗑️  Deleting {len(versions)} object versions...")
            try:
                total_batches = (len(versions) + 999) // 1000
                for i in range(0, len(versions), 1000):
                    batch = versions[i:i + 1000]
                    batch_num = i // 1000 + 1
                    
                    delete_request = {
                        'Objects': [{'Key': obj['Key'], 'VersionId': obj['VersionId']} for obj in batch]
                    }
                    
                    response = self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete=delete_request
                    )
                    
                    batch_deleted = len(response.get('Deleted', []))
                    results['versions_deleted'] += batch_deleted
                    
                    # Progress logging
                    progress = (batch_num / total_batches) * 100
                    print(f"   📦 Batch {batch_num}/{total_batches} ({progress:.1f}%): deleted {batch_deleted} versions")
                    
                    if 'Errors' in response:
                        for error in response['Errors']:
                            results['errors'].append(f"Version {error['Key']}: {error['Message']}")
                            
            except ClientError as e:
                results['errors'].append(f"Failed to delete versions: {e}")
        
        # Delete delete markers
        if delete_markers:
            print(f"🗑️  Deleting {len(delete_markers)} delete markers...")
            try:
                total_batches = (len(delete_markers) + 999) // 1000
                for i in range(0, len(delete_markers), 1000):
                    batch = delete_markers[i:i + 1000]
                    batch_num = i // 1000 + 1
                    
                    delete_request = {
                        'Objects': [{'Key': obj['Key'], 'VersionId': obj['VersionId']} for obj in batch]
                    }
                    
                    response = self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete=delete_request
                    )
                    
                    batch_deleted = len(response.get('Deleted', []))
                    results['delete_markers_deleted'] += batch_deleted
                    
                    # Progress logging
                    progress = (batch_num / total_batches) * 100
                    print(f"   📦 Batch {batch_num}/{total_batches} ({progress:.1f}%): deleted {batch_deleted} markers")
                    
                    if 'Errors' in response:
                        for error in response['Errors']:
                            results['errors'].append(f"Delete marker {error['Key']}: {error['Message']}")
                            
            except ClientError as e:
                results['errors'].append(f"Failed to delete delete markers: {e}")
        
        return results
    
    def deep_clean_folder(self, folder_prefix: str) -> bool:
        """Completely clean a folder including all hidden objects"""
        print(f"🔍 Deep scanning folder: {folder_prefix}")
        
        # Ensure folder prefix ends with /
        if not folder_prefix.endswith('/'):
            folder_prefix += '/'
        
        # List all objects
        all_objects = self.list_all_objects(folder_prefix)
        
        if not all_objects:
            print(f"✅ Folder {folder_prefix} is already completely clean")
            return True
        
        # Group and count objects by type
        object_counts = {}
        for obj in all_objects:
            obj_type = obj['Type']
            object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
        
        print(f"📊 Found objects in {folder_prefix}:")
        for obj_type, count in object_counts.items():
            print(f"   - {obj_type}: {count}")
        
        # Confirm deletion
        total_items = len(all_objects)
        
        # Estimate time
        estimated_seconds = total_items / 1000 * 2  # Rough estimate: 2 seconds per 1000 items
        estimated_minutes = estimated_seconds / 60
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total items to delete: {total_items:,}")
        print(f"   Estimated time: ~{estimated_minutes:.1f} minutes")
        
        response = input(f"\n🚨 Delete ALL {total_items:,} items from {folder_prefix}? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("❌ Operation cancelled")
            return False
        
        # Perform deep deletion
        print(f"\n🗑️  Starting deep deletion of {total_items} items...")
        start_time = datetime.now()
        
        results = self.delete_all_objects(all_objects)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Show results
        print(f"\n✅ Deep deletion completed!")
        print(f"⏱️  Duration: {duration}")
        print(f"🗑️  Regular objects deleted: {results['objects_deleted']}")
        print(f"🚫 Multipart uploads aborted: {results['multipart_aborted']}")
        print(f"🗑️  Object versions deleted: {results['versions_deleted']}")
        print(f"🗑️  Delete markers deleted: {results['delete_markers_deleted']}")
        
        if results['errors']:
            print(f"❌ Errors: {len(results['errors'])}")
            for error in results['errors'][:5]:
                print(f"   - {error}")
            if len(results['errors']) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")
        
        # Verify folder is gone
        print(f"\n🔍 Verifying folder is completely removed...")
        remaining_objects = self.list_all_objects(folder_prefix)
        
        if remaining_objects:
            print(f"⚠️  Warning: {len(remaining_objects)} objects still remain")
            return False
        else:
            print(f"✅ Folder {folder_prefix} is completely removed!")
            return True

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='S3 Deep Folder Clean - Remove folders completely')
    parser.add_argument('--folder', required=True, help='Folder prefix to clean completely')
    
    args = parser.parse_args()
    
    cleaner = S3DeepFolderCleaner()
    
    folder_prefix = args.folder.rstrip('/')
    
    try:
        success = cleaner.deep_clean_folder(folder_prefix)
        
        if success:
            print(f"\n🎉 Folder {folder_prefix} has been completely removed!")
            print(f"💡 Try refreshing your S3 console - the folder should be gone now")
        else:
            print(f"\n❌ Failed to completely remove folder {folder_prefix}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()