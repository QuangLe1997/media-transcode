#!/usr/bin/env python3
"""
S3 Ultra Delete - Maximum performance S3 deletion
Optimized for delete markers and versioned objects
"""

import concurrent.futures
import sys
import threading
import time
from pathlib import Path
from typing import List

import boto3

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from config import settings


class S3UltraDelete:
    """Ultra-fast S3 deletion optimized for all object types"""

    def __init__(self, max_threads: int = 200):
        self.bucket_name = settings.aws_bucket_name
        self.max_threads = max_threads
        self.deleted_count = 0
        self.lock = threading.Lock()

        # S3 connection config
        self.s3_config = {
            'endpoint_url': settings.aws_endpoint_url,
            'aws_access_key_id': settings.aws_access_key_id,
            'aws_secret_access_key': settings.aws_secret_access_key,
            'region_name': 'us-east-1'
        }

    def scan_delete_markers(self, folder_prefix: str) -> List[dict]:
        """Quickly scan for delete markers"""
        print(f"🔍 Scanning delete markers in: {folder_prefix}")

        s3_client = boto3.client('s3', **self.s3_config)
        markers = []

        try:
            paginator = s3_client.get_paginator('list_object_versions')

            for page_num, page in enumerate(paginator.paginate(
                    Bucket=self.bucket_name,
                    Prefix=folder_prefix,
                    PaginationConfig={'PageSize': 1000}
            )):
                if 'DeleteMarkers' in page:
                    for marker in page['DeleteMarkers']:
                        markers.append({
                            'Key': marker['Key'],
                            'VersionId': marker['VersionId']
                        })

                if page_num % 10 == 0 and markers:
                    print(f"   📋 Found {len(markers):,} delete markers...")

        except Exception as e:
            print(f"❌ Error scanning delete markers: {e}")

        print(f"✅ Total delete markers found: {len(markers):,}")
        return markers

    def delete_markers_batch(self, markers: List[dict], batch_num: int) -> dict:
        """Delete a batch of delete markers"""
        s3_client = boto3.client('s3', **self.s3_config)

        try:
            delete_request = {
                'Objects': markers
            }

            response = s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete=delete_request
            )

            deleted = len(response.get('Deleted', []))

            with self.lock:
                self.deleted_count += deleted

            return {'batch_num': batch_num, 'deleted': deleted, 'success': True}

        except Exception as e:
            return {'batch_num': batch_num, 'deleted': 0, 'error': str(e), 'success': False}

    def ultra_delete_markers(self, folder_prefix: str, batch_size: int = 1000) -> bool:
        """Ultra-fast deletion of delete markers"""

        # Ensure folder prefix ends with /
        if not folder_prefix.endswith('/'):
            folder_prefix += '/'

        # Scan all delete markers
        start_time = time.time()
        all_markers = self.scan_delete_markers(folder_prefix)

        if not all_markers:
            print("✅ No delete markers to clean")
            return True

        # Prepare batches
        batches = []
        for i in range(0, len(all_markers), batch_size):
            batch = all_markers[i:i + batch_size]
            batches.append((batch, len(batches) + 1))

        total_batches = len(batches)

        print(f"\n🚀 ULTRA DELETE MODE!")
        print(f"📦 Total delete markers: {len(all_markers):,}")
        print(f"📦 Total batches: {total_batches}")
        print(f"🔥 Thread pool: {self.max_threads} threads")
        print(f"⚡ Starting ultra-fast deletion...\n")

        completed = 0

        # Progress callback
        def print_progress(future):
            nonlocal completed
            result = future.result()
            completed += 1

            progress = (completed / total_batches) * 100
            elapsed = time.time() - start_time
            rate = self.deleted_count / elapsed if elapsed > 0 else 0

            print(f"⚡ Batch {completed}/{total_batches} ({progress:.1f}%) | "
                  f"Speed: {rate:.0f} markers/sec | "
                  f"Deleted: {self.deleted_count:,}")

        # Execute with massive parallelization
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = []

            for batch, batch_num in batches:
                future = executor.submit(self.delete_markers_batch, batch, batch_num)
                future.add_done_callback(print_progress)
                futures.append(future)

            concurrent.futures.wait(futures)

        # Results
        elapsed = time.time() - start_time

        print(f"\n{'=' * 60}")
        print(f"🎉 ULTRA DELETE COMPLETED!")
        print(f"⏱️  Time: {elapsed:.1f} seconds")
        print(f"✅ Delete markers removed: {self.deleted_count:,}")
        print(f"⚡ Speed: {self.deleted_count / elapsed:.0f} markers/second")
        print(f"{'=' * 60}")

        return True


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='S3 Ultra Delete - Maximum performance')
    parser.add_argument('--folder', required=True, help='Folder to clean')
    parser.add_argument('--threads', type=int, default=200, help='Number of threads (default: 200)')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size (default: 1000)')

    args = parser.parse_args()

    print(f"🚀 S3 ULTRA DELETE - DELETE MARKERS")
    print(f"📁 Bucket: {settings.aws_bucket_name}")
    print(f"📂 Folder: {args.folder}")
    print(f"🔥 Threads: {args.threads}")

    try:
        deleter = S3UltraDelete(max_threads=args.threads)
        success = deleter.ultra_delete_markers(args.folder, batch_size=args.batch_size)

        if not success:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
