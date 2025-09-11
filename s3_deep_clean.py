#!/usr/bin/env python3
"""
S3 Deep Clean Script
Safely remove dev-facefusion-media/transcode-service folder and all its contents
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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f's3_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


class S3DeepCleaner:
    """S3 Deep Cleaner for removing old folder structures"""
    
    def __init__(self):
        """Initialize S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.aws_endpoint_url,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name='us-east-1'  # Default region for S3
            )
            self.bucket_name = settings.aws_bucket_name
            logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please check your configuration.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            sys.exit(1)
    
    def list_folder_contents(self, folder_prefix: str, max_items: int = 1000) -> List[Dict]:
        """List all objects in a folder with details"""
        try:
            objects = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=folder_prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects.append({
                            'Key': obj['Key'],
                            'Size': obj['Size'],
                            'LastModified': obj['LastModified'],
                            'StorageClass': obj.get('StorageClass', 'STANDARD')
                        })
                        
                        # Limit items to avoid memory issues
                        if len(objects) >= max_items:
                            logger.warning(f"Reached max items limit ({max_items}). There may be more files.")
                            break
                    
                    if len(objects) >= max_items:
                        break
            
            logger.info(f"Found {len(objects)} objects in {folder_prefix}")
            return objects
            
        except ClientError as e:
            logger.error(f"Error listing objects: {e}")
            return []
    
    def calculate_folder_size(self, objects: List[Dict]) -> Dict:
        """Calculate total size and file count statistics"""
        total_size = sum(obj['Size'] for obj in objects)
        file_count = len(objects)
        
        # Convert size to human readable format
        def format_size(size_bytes):
            if size_bytes == 0:
                return "0 B"
            size_names = ["B", "KB", "MB", "GB", "TB"]
            i = 0
            while size_bytes >= 1024 and i < len(size_names) - 1:
                size_bytes /= 1024.0
                i += 1
            return f"{size_bytes:.2f} {size_names[i]}"
        
        # Group by file extension
        extensions = {}
        for obj in objects:
            ext = Path(obj['Key']).suffix.lower() or 'no_extension'
            if ext not in extensions:
                extensions[ext] = {'count': 0, 'size': 0}
            extensions[ext]['count'] += 1
            extensions[ext]['size'] += obj['Size']
        
        return {
            'total_size': total_size,
            'total_size_formatted': format_size(total_size),
            'file_count': file_count,
            'extensions': extensions
        }
    
    def confirm_deletion(self, folder_prefix: str, stats: Dict) -> bool:
        """Get user confirmation before deletion"""
        print("\n" + "="*80)
        print(f"🚨 DANGER: You are about to DELETE the following S3 folder:")
        print(f"📁 Bucket: {self.bucket_name}")
        print(f"📂 Folder: {folder_prefix}")
        print(f"📊 Total Files: {stats['file_count']:,}")
        print(f"💾 Total Size: {stats['total_size_formatted']}")
        print("\n📋 File breakdown:")
        
        for ext, data in sorted(stats['extensions'].items()):
            size_formatted = self.format_size(data['size'])
            print(f"   {ext}: {data['count']:,} files ({size_formatted})")
        
        print("\n⚠️  WARNING: This action CANNOT be undone!")
        print("="*80)
        
        # Triple confirmation
        confirmations = [
            "Are you absolutely sure you want to delete this folder? (yes/no): ",
            "This will permanently delete ALL files. Type 'DELETE' to confirm: ",
            f"Final confirmation - type the folder name '{folder_prefix}' to proceed: "
        ]
        
        expected_responses = ["yes", "DELETE", folder_prefix]
        
        for i, (prompt, expected) in enumerate(zip(confirmations, expected_responses)):
            response = input(prompt).strip()
            if response != expected:
                print(f"❌ Deletion cancelled. Expected '{expected}', got '{response}'")
                return False
        
        print("✅ Deletion confirmed. Proceeding...")
        return True
    
    def format_size(self, size_bytes):
        """Format bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.2f} {size_names[i]}"
    
    def delete_objects_batch(self, objects: List[Dict], batch_size: int = 1000) -> Dict:
        """Delete objects in batches"""
        deleted_count = 0
        failed_count = 0
        errors = []
        
        # Process in batches
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            
            try:
                # Prepare delete request
                delete_request = {
                    'Objects': [{'Key': obj['Key']} for obj in batch]
                }
                
                # Execute batch delete
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete=delete_request
                )
                
                # Count successful deletions
                deleted_count += len(response.get('Deleted', []))
                
                # Handle errors
                if 'Errors' in response:
                    for error in response['Errors']:
                        failed_count += 1
                        errors.append(f"Failed to delete {error['Key']}: {error['Message']}")
                        logger.error(f"Failed to delete {error['Key']}: {error['Message']}")
                
                logger.info(f"Deleted batch {i//batch_size + 1}: {len(batch)} objects")
                
            except ClientError as e:
                failed_count += len(batch)
                error_msg = f"Batch deletion failed: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            'deleted_count': deleted_count,
            'failed_count': failed_count,
            'errors': errors
        }
    
    def deep_clean_folder(self, folder_prefix: str, dry_run: bool = False) -> bool:
        """Deep clean a folder with safety checks"""
        logger.info(f"Starting deep clean for folder: {folder_prefix}")
        
        # Step 1: List all objects
        print(f"🔍 Scanning folder: {folder_prefix}")
        objects = self.list_folder_contents(folder_prefix)
        
        if not objects:
            print(f"✅ No objects found in {folder_prefix}")
            return True
        
        # Step 2: Calculate statistics
        stats = self.calculate_folder_size(objects)
        
        # Step 3: Show preview for dry run
        if dry_run:
            print(f"\n🔍 DRY RUN - Preview of what would be deleted:")
            print(f"📁 Folder: {folder_prefix}")
            print(f"📊 Files: {stats['file_count']:,}")
            print(f"💾 Size: {stats['total_size_formatted']}")
            print("\n📋 File breakdown:")
            for ext, data in sorted(stats['extensions'].items()):
                size_formatted = self.format_size(data['size'])
                print(f"   {ext}: {data['count']:,} files ({size_formatted})")
            return True
        
        # Step 4: Get user confirmation
        if not self.confirm_deletion(folder_prefix, stats):
            return False
        
        # Step 5: Perform deletion
        print(f"\n🗑️  Deleting {stats['file_count']:,} objects...")
        start_time = datetime.now()
        
        result = self.delete_objects_batch(objects)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Step 6: Report results
        print(f"\n✅ Deletion completed!")
        print(f"⏱️  Duration: {duration}")
        print(f"✅ Successfully deleted: {result['deleted_count']:,} objects")
        
        if result['failed_count'] > 0:
            print(f"❌ Failed to delete: {result['failed_count']:,} objects")
            print("📋 Errors:")
            for error in result['errors'][:10]:  # Show first 10 errors
                print(f"   - {error}")
            if len(result['errors']) > 10:
                print(f"   ... and {len(result['errors']) - 10} more errors")
        
        return result['failed_count'] == 0


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='S3 Deep Clean Script')
    parser.add_argument('--folder', required=True, help='Folder prefix to clean (e.g., dev-facefusion-media/transcode-service)')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be deleted without actually deleting')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts (dangerous!)')
    
    args = parser.parse_args()
    
    # Initialize cleaner
    cleaner = S3DeepCleaner()
    
    # Validate folder prefix
    folder_prefix = args.folder.rstrip('/')
    if not folder_prefix:
        print("❌ Error: Folder prefix cannot be empty")
        sys.exit(1)
    
    # Add trailing slash for proper folder matching
    folder_prefix += '/'
    
    try:
        # Perform deep clean
        success = cleaner.deep_clean_folder(folder_prefix, dry_run=args.dry_run)
        
        if success:
            if args.dry_run:
                print(f"\n✅ Dry run completed successfully")
            else:
                print(f"\n✅ Deep clean completed successfully")
        else:
            print(f"\n❌ Deep clean failed or was cancelled")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()