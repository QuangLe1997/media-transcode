#!/usr/bin/env python3
"""
S3 Bulk Clean Script
Delete multiple S3 folders/prefixes at once with single confirmation
"""

import os
import sys
import boto3
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime
import concurrent.futures
import threading

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
        logging.FileHandler(f's3_bulk_cleanup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class S3BulkCleaner:
    """S3 Bulk Cleaner for removing multiple folders at once"""
    
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
            self.stats_lock = threading.Lock()
            logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please check your configuration.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            sys.exit(1)
    
    def scan_folder(self, folder_prefix: str) -> Tuple[List[Dict], Dict]:
        """Scan a single folder and return objects and stats"""
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
                            'Folder': folder_prefix
                        })
            
            # Calculate stats
            total_size = sum(obj['Size'] for obj in objects)
            stats = {
                'folder': folder_prefix,
                'count': len(objects),
                'size': total_size,
                'size_formatted': self.format_size(total_size)
            }
            
            return objects, stats
            
        except ClientError as e:
            logger.error(f"Error scanning {folder_prefix}: {e}")
            return [], {'folder': folder_prefix, 'count': 0, 'size': 0, 'size_formatted': '0 B'}
    
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
    
    def scan_multiple_folders(self, folder_prefixes: List[str]) -> Tuple[List[Dict], List[Dict]]:
        """Scan multiple folders concurrently"""
        print(f"🔍 Scanning {len(folder_prefixes)} folders...")
        
        all_objects = []
        all_stats = []
        
        # Use thread pool for concurrent scanning
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all scan tasks
            future_to_folder = {
                executor.submit(self.scan_folder, folder): folder 
                for folder in folder_prefixes
            }
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_folder):
                folder = future_to_folder[future]
                try:
                    objects, stats = future.result()
                    all_objects.extend(objects)
                    all_stats.append(stats)
                    
                    if stats['count'] > 0:
                        print(f"✅ {folder}: {stats['count']:,} files ({stats['size_formatted']})")
                    else:
                        print(f"⚪ {folder}: empty")
                        
                except Exception as e:
                    logger.error(f"Error scanning {folder}: {e}")
                    print(f"❌ {folder}: error - {e}")
        
        return all_objects, all_stats
    
    def show_summary(self, all_stats: List[Dict]) -> Dict:
        """Show summary of all folders to be deleted"""
        non_empty_stats = [s for s in all_stats if s['count'] > 0]
        
        if not non_empty_stats:
            print("✅ All folders are empty - nothing to delete")
            return {'total_files': 0, 'total_size': 0}
        
        total_files = sum(s['count'] for s in non_empty_stats)
        total_size = sum(s['size'] for s in non_empty_stats)
        
        print(f"\n📊 BULK DELETION SUMMARY:")
        print(f"📁 Folders to delete: {len(non_empty_stats)}")
        print(f"📄 Total files: {total_files:,}")
        print(f"💾 Total size: {self.format_size(total_size)}")
        
        print(f"\n📋 Breakdown by folder:")
        for stats in sorted(non_empty_stats, key=lambda x: x['size'], reverse=True):
            print(f"   📂 {stats['folder']}: {stats['count']:,} files ({stats['size_formatted']})")
        
        return {'total_files': total_files, 'total_size': total_size}
    
    def confirm_bulk_deletion(self, summary: Dict) -> bool:
        """Get single confirmation for bulk deletion"""
        if summary['total_files'] == 0:
            return False
        
        print(f"\n🚨 WARNING: BULK DELETION")
        print(f"📊 Total files to delete: {summary['total_files']:,}")
        print(f"💾 Total size: {self.format_size(summary['total_size'])}")
        print(f"⚠️  This action CANNOT be undone!")
        
        response = input(f"\nType 'DELETE ALL' to confirm bulk deletion: ").strip()
        
        if response != 'DELETE ALL':
            print(f"❌ Bulk deletion cancelled. Expected 'DELETE ALL', got '{response}'")
            return False
        
        print("✅ Bulk deletion confirmed!")
        return True
    
    def delete_objects_batch(self, objects: List[Dict], batch_size: int = 1000, max_threads: int = 100) -> Dict:
        """Delete objects in batches using thread pool for parallel execution"""
        import queue
        import time
        
        deleted_count = 0
        failed_count = 0
        errors = []
        
        # Thread-safe counters
        results_queue = queue.Queue()
        
        # Prepare batches
        batches = []
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            batch_num = i // batch_size + 1
            batches.append((batch_num, batch))
        
        total_batches = len(batches)
        print(f"🚀 Starting parallel deletion with {max_threads} threads...")
        print(f"📦 Total batches to process: {total_batches}")
        
        def delete_batch(batch_info):
            """Delete a single batch in a thread"""
            batch_num, batch = batch_info
            
            try:
                # Create new S3 client for this thread
                thread_s3_client = boto3.client(
                    's3',
                    endpoint_url=settings.aws_endpoint_url,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name='us-east-1'
                )
                
                # Prepare delete request
                delete_request = {
                    'Objects': [{'Key': obj['Key']} for obj in batch]
                }
                
                # Execute batch delete
                response = thread_s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete=delete_request
                )
                
                # Count successful deletions
                batch_deleted = len(response.get('Deleted', []))
                batch_errors = []
                
                # Handle errors
                if 'Errors' in response:
                    for error in response['Errors']:
                        batch_errors.append(f"Failed to delete {error['Key']}: {error['Message']}")
                
                results_queue.put({
                    'batch_num': batch_num,
                    'deleted': batch_deleted,
                    'failed': len(batch_errors),
                    'errors': batch_errors,
                    'success': True
                })
                
            except Exception as e:
                results_queue.put({
                    'batch_num': batch_num,
                    'deleted': 0,
                    'failed': len(batch),
                    'errors': [f"Batch {batch_num} failed: {e}"],
                    'success': False
                })
        
        # Start timer
        start_time = time.time()
        completed = 0
        
        # Process batches with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Submit all batches
            futures = []
            for batch_info in batches:
                future = executor.submit(delete_batch, batch_info)
                futures.append(future)
            
            # Monitor progress
            while completed < total_batches:
                # Check for completed batches
                while not results_queue.empty():
                    result = results_queue.get()
                    completed += 1
                    
                    deleted_count += result['deleted']
                    failed_count += result['failed']
                    errors.extend(result['errors'])
                    
                    # Calculate progress
                    progress = (completed / total_batches) * 100
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (total_batches - completed) / rate if rate > 0 else 0
                    
                    print(f"🗑️  Progress: {completed}/{total_batches} ({progress:.1f}%) | "
                          f"Rate: {rate:.1f} batches/sec | ETA: {eta:.1f}s | "
                          f"Deleted: {deleted_count:,}")
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.1)
            
            # Wait for all futures to complete
            concurrent.futures.wait(futures)
        
        # Process any remaining results
        while not results_queue.empty():
            result = results_queue.get()
            deleted_count += result['deleted']
            failed_count += result['failed']
            errors.extend(result['errors'])
        
        # Final stats
        elapsed = time.time() - start_time
        print(f"\n✅ Parallel deletion completed in {elapsed:.1f} seconds")
        print(f"⚡ Average speed: {deleted_count/elapsed:.1f} objects/second")
        
        return {
            'deleted_count': deleted_count,
            'failed_count': failed_count,
            'errors': errors
        }
    
    def bulk_delete_folders(self, folder_prefixes: List[str], dry_run: bool = False) -> bool:
        """Delete multiple folders with single confirmation"""
        # Add trailing slash to folder prefixes
        folder_prefixes = [f.rstrip('/') + '/' for f in folder_prefixes]
        
        logger.info(f"Starting bulk deletion for {len(folder_prefixes)} folders")
        
        # Step 1: Scan all folders
        all_objects, all_stats = self.scan_multiple_folders(folder_prefixes)
        
        # Step 2: Show summary
        summary = self.show_summary(all_stats)
        
        if summary['total_files'] == 0:
            return True
        
        # Step 3: Dry run preview
        if dry_run:
            print(f"\n🔍 DRY RUN - Preview completed")
            print(f"📊 Would delete {summary['total_files']:,} files ({self.format_size(summary['total_size'])})")
            return True
        
        # Step 4: Get confirmation
        if not self.confirm_bulk_deletion(summary):
            return False
        
        # Step 5: Perform bulk deletion
        print(f"\n🗑️  Starting bulk deletion of {summary['total_files']:,} objects...")
        start_time = datetime.now()
        
        result = self.delete_objects_batch(all_objects)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Step 6: Show results
        print(f"\n✅ Bulk deletion completed!")
        print(f"⏱️  Duration: {duration}")
        print(f"✅ Successfully deleted: {result['deleted_count']:,} objects")
        
        if result['failed_count'] > 0:
            print(f"❌ Failed to delete: {result['failed_count']:,} objects")
            if result['errors']:
                print("📋 Sample errors:")
                for error in result['errors'][:5]:
                    print(f"   - {error}")
                if len(result['errors']) > 5:
                    print(f"   ... and {len(result['errors']) - 5} more errors")
        
        return result['failed_count'] == 0


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='S3 Bulk Clean Script')
    parser.add_argument('--folders', nargs='+', required=True, help='List of folder prefixes to clean')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be deleted')
    parser.add_argument('--common-patterns', action='store_true', help='Include common old folder patterns')
    
    args = parser.parse_args()
    
    # Initialize cleaner
    cleaner = S3BulkCleaner()
    
    # Base folders to clean
    folders_to_clean = args.folders
    
    # Add common patterns if requested
    if args.common_patterns:
        common_patterns = [
            'dev-facefusion-media/transcode-service',
            'transcode-service',
            'old-transcode-outputs',
            'temp-uploads',
            'test-outputs'
        ]
        folders_to_clean.extend(common_patterns)
        print(f"📋 Added common patterns: {common_patterns}")
    
    # Remove duplicates
    folders_to_clean = list(set(folders_to_clean))
    
    print(f"🧹 S3 Bulk Cleaner")
    print(f"📁 Bucket: {cleaner.bucket_name}")
    print(f"📂 Folders to process: {len(folders_to_clean)}")
    
    try:
        success = cleaner.bulk_delete_folders(folders_to_clean, dry_run=args.dry_run)
        
        if success:
            if args.dry_run:
                print(f"\n✅ Bulk scan completed successfully")
            else:
                print(f"\n✅ Bulk deletion completed successfully")
        else:
            print(f"\n❌ Bulk operation failed or was cancelled")
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