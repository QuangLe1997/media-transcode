#!/usr/bin/env python3
"""
S3 Turbo Delete - Ultra-fast parallel S3 deletion with 100+ threads
"""

import os
import sys
import boto3
import logging
from pathlib import Path
from typing import List, Dict
from botocore.exceptions import ClientError
import concurrent.futures
import threading
import time
import queue
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

class S3TurboDelete:
    """Ultra-fast S3 deletion with massive parallelization"""
    
    def __init__(self, max_threads: int = 100):
        """Initialize with configurable thread count"""
        self.bucket_name = settings.aws_bucket_name
        self.max_threads = max_threads
        self.deleted_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()
        
        # Create a pool of S3 clients for threads to use
        self.s3_client_pool = queue.Queue()
        print(f"🚀 Initializing S3 Turbo Delete with {max_threads} threads...")
        
        # Pre-create S3 clients for the thread pool
        for _ in range(min(max_threads, 50)):  # Cap at 50 clients
            client = boto3.client(
                's3',
                endpoint_url=settings.aws_endpoint_url,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name='us-east-1'
            )
            self.s3_client_pool.put(client)
        
        print(f"✅ Initialized {self.s3_client_pool.qsize()} S3 clients")
    
    def get_s3_client(self):
        """Get an S3 client from the pool or create new one"""
        try:
            return self.s3_client_pool.get_nowait()
        except queue.Empty:
            # Create new client if pool is empty
            return boto3.client(
                's3',
                endpoint_url=settings.aws_endpoint_url,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name='us-east-1'
            )
    
    def return_s3_client(self, client):
        """Return S3 client to the pool"""
        try:
            self.s3_client_pool.put_nowait(client)
        except queue.Full:
            pass  # Pool is full, discard client
    
    def list_all_objects(self, folder_prefix: str, max_keys: int = None) -> List[str]:
        """List all object keys in a folder"""
        print(f"🔍 Scanning folder: {folder_prefix}")
        
        s3_client = self.get_s3_client()
        all_keys = []
        
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=folder_prefix,
                PaginationConfig={
                    'PageSize': 1000
                }
            )
            
            for page_num, page in enumerate(page_iterator):
                if 'Contents' in page:
                    keys = [obj['Key'] for obj in page['Contents']]
                    all_keys.extend(keys)
                    
                    if page_num % 10 == 0:
                        print(f"   📄 Scanned {len(all_keys):,} objects...")
                    
                    if max_keys and len(all_keys) >= max_keys:
                        all_keys = all_keys[:max_keys]
                        break
            
            print(f"✅ Found {len(all_keys):,} objects to delete")
            
        finally:
            self.return_s3_client(s3_client)
        
        return all_keys
    
    def delete_batch(self, keys: List[str], batch_num: int, total_batches: int) -> Dict:
        """Delete a batch of objects"""
        s3_client = self.get_s3_client()
        
        try:
            delete_request = {
                'Objects': [{'Key': key} for key in keys]
            }
            
            response = s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete=delete_request
            )
            
            deleted = len(response.get('Deleted', []))
            failed = len(response.get('Errors', []))
            
            # Update counters thread-safely
            with self.lock:
                self.deleted_count += deleted
                self.failed_count += failed
            
            return {
                'batch_num': batch_num,
                'deleted': deleted,
                'failed': failed,
                'success': True
            }
            
        except Exception as e:
            with self.lock:
                self.failed_count += len(keys)
            
            return {
                'batch_num': batch_num,
                'deleted': 0,
                'failed': len(keys),
                'error': str(e),
                'success': False
            }
        
        finally:
            self.return_s3_client(s3_client)
    
    def turbo_delete(self, folder_prefix: str, batch_size: int = 1000, confirm: bool = True) -> bool:
        """Delete folder with turbo speed using massive parallelization"""
        
        # Ensure folder prefix ends with /
        if not folder_prefix.endswith('/'):
            folder_prefix += '/'
        
        # List all objects
        start_time = time.time()
        all_keys = self.list_all_objects(folder_prefix)
        
        if not all_keys:
            print("✅ No objects to delete")
            return True
        
        # Confirm deletion
        if confirm:
            response = input(f"\n🚨 Delete {len(all_keys):,} objects? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Operation cancelled")
                return False
        
        # Prepare batches
        batches = []
        for i in range(0, len(all_keys), batch_size):
            batch_keys = all_keys[i:i + batch_size]
            batch_num = len(batches) + 1
            batches.append((batch_keys, batch_num))
        
        total_batches = len(batches)
        
        print(f"\n🚀 TURBO DELETE MODE ACTIVATED!")
        print(f"📦 Total batches: {total_batches}")
        print(f"🔥 Thread pool size: {self.max_threads}")
        print(f"⚡ Starting parallel deletion...\n")
        
        # Progress tracking
        completed_batches = 0
        progress_lock = threading.Lock()
        
        def update_progress(future):
            nonlocal completed_batches
            
            result = future.result()
            
            with progress_lock:
                completed_batches += 1
                progress = (completed_batches / total_batches) * 100
                elapsed = time.time() - start_time
                rate = self.deleted_count / elapsed if elapsed > 0 else 0
                
                print(f"⚡ Batch {result['batch_num']}/{total_batches} ({progress:.1f}%) | "
                      f"Speed: {rate:.0f} obj/sec | "
                      f"Deleted: {self.deleted_count:,} | "
                      f"Failed: {self.failed_count:,}")
        
        # Execute parallel deletion
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = []
            
            # Submit all batches
            for batch_keys, batch_num in batches:
                future = executor.submit(self.delete_batch, batch_keys, batch_num, total_batches)
                future.add_done_callback(update_progress)
                futures.append(future)
            
            # Wait for all to complete
            concurrent.futures.wait(futures)
        
        # Final results
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"🎉 TURBO DELETE COMPLETED!")
        print(f"⏱️  Total time: {elapsed:.1f} seconds")
        print(f"✅ Objects deleted: {self.deleted_count:,}")
        print(f"❌ Failed deletions: {self.failed_count:,}")
        print(f"⚡ Average speed: {self.deleted_count/elapsed:.0f} objects/second")
        print(f"🚀 Performance: {len(all_keys)/elapsed:.0f} operations/second")
        print(f"{'='*60}")
        
        return self.failed_count == 0

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='S3 Turbo Delete - Ultra-fast deletion')
    parser.add_argument('--folder', required=True, help='Folder to delete')
    parser.add_argument('--threads', type=int, default=100, help='Number of threads (default: 100)')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size (default: 1000)')
    parser.add_argument('--no-confirm', action='store_true', help='Skip confirmation')
    parser.add_argument('--max-objects', type=int, help='Maximum objects to delete (for testing)')
    
    args = parser.parse_args()
    
    print(f"🚀 S3 TURBO DELETE")
    print(f"📁 Bucket: {settings.aws_bucket_name}")
    print(f"📂 Folder: {args.folder}")
    print(f"🔥 Threads: {args.threads}")
    print(f"📦 Batch size: {args.batch_size}")
    
    try:
        # Create turbo deleter
        deleter = S3TurboDelete(max_threads=args.threads)
        
        # Override list method if max_objects is specified
        if args.max_objects:
            print(f"⚠️  Limited to {args.max_objects} objects (testing mode)")
            original_list = deleter.list_all_objects
            deleter.list_all_objects = lambda folder: original_list(folder, args.max_objects)
        
        # Execute turbo delete
        success = deleter.turbo_delete(
            args.folder,
            batch_size=args.batch_size,
            confirm=not args.no_confirm
        )
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()