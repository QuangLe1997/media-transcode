import logging
import mimetypes
import os
from typing import BinaryIO, Optional

import boto3
from botocore.exceptions import ClientError

from ..core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self):
        from botocore.config import Config

        # Config cho file lớn
        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            read_timeout=900,  # 15 minutes
            connect_timeout=60,
            max_pool_connections=50,
        )

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            config=config,
        )
        self.bucket_name = settings.aws_bucket_name
        self.base_folder = settings.aws_base_folder
        self.public_url = settings.aws_endpoint_public_url

    def _get_full_key(self, key: str, custom_base_folder: str = None) -> str:
        """Get full S3 key with base folder prefix"""
        base_folder = custom_base_folder if custom_base_folder is not None else self.base_folder
        return f"{base_folder}/{key}" if base_folder else key

    def _get_content_type_by_extension(self, file_path: str) -> Optional[str]:
        """Get content type based on file extension with explicit mappings for media files"""
        ext = os.path.splitext(file_path)[1].lower()

        # Explicit mappings for media files to ensure proper browser playback
        content_type_mapping = {
            # Video formats
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".mkv": "video/x-matroska",
            ".m4v": "video/mp4",
            # Image formats
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
            # Audio formats
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".aac": "audio/aac",
            ".m4a": "audio/mp4",
            # Other formats
            ".json": "application/json",
            ".txt": "text/plain",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
        }

        return content_type_mapping.get(ext)

    def upload_file(self, file_data: BinaryIO, key: str, content_type: Optional[str] = None) -> str:
        """Upload file to S3 and return public URL"""
        try:
            full_key = self._get_full_key(key)

            # Determine content type if not provided
            if not content_type:
                content_type = (
                        self._get_content_type_by_extension(key)
                        or mimetypes.guess_type(key)[0]
                        or "application/octet-stream"
                )

            # Set content disposition for proper browser handling
            content_disposition = "inline"
            if content_type.startswith("video/") or content_type.startswith("audio/"):
                content_disposition = 'inline; filename="' + os.path.basename(key) + '"'

            extra_args = {
                "ContentType": content_type,
                # 1 year cache for better web performance
                "CacheControl": "public, max-age=31536000",
                "ContentDisposition": content_disposition,
            }

            # Optimize cache control based on content type
            if content_type.startswith("image/"):
                # 1 year for images
                extra_args["CacheControl"] = "public, max-age=31536000"
            elif content_type.startswith("video/") or content_type.startswith("audio/"):
                # 30 days for videos/audio
                extra_args["CacheControl"] = "public, max-age=2592000"
                # Add additional headers for video streaming
                # Enable range requests for video streaming
                extra_args["AcceptRanges"] = "bytes"

            self.s3_client.upload_fileobj(
                file_data, self.bucket_name, full_key, ExtraArgs=extra_args
            )

            public_url = f"{self.public_url}/{self.bucket_name}/{full_key}"
            logger.info(f"Uploaded file to S3: {full_key}")
            return public_url

        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            raise

    def upload_file_from_path(
            self,
            file_path: str,
            key: str,
            custom_base_folder: str = None,
            skip_base_folder: bool = False,
    ) -> str:
        """Upload file from local path to S3"""
        try:
            if skip_base_folder:
                full_key = key
            else:
                full_key = self._get_full_key(key, custom_base_folder)

            # Determine content type
            content_type = (
                    self._get_content_type_by_extension(file_path)
                    or mimetypes.guess_type(file_path)[0]
                    or "application/octet-stream"
            )

            # Set content disposition for proper browser handling
            content_disposition = "inline"
            if content_type.startswith("video/") or content_type.startswith("audio/"):
                content_disposition = 'inline; filename="' + os.path.basename(file_path) + '"'

            extra_args = {
                "ContentType": content_type,
                # 1 year cache for better web performance
                "CacheControl": "public, max-age=31536000",
                "ContentDisposition": content_disposition,
            }

            # Optimize cache control based on content type
            if content_type.startswith("image/"):
                # 1 year for images
                extra_args["CacheControl"] = "public, max-age=31536000"
            elif content_type.startswith("video/") or content_type.startswith("audio/"):
                # 30 days for videos/audio
                extra_args["CacheControl"] = "public, max-age=2592000"
                # Add additional headers for video streaming
                # Enable range requests for video streaming
                extra_args["AcceptRanges"] = "bytes"

            self.s3_client.upload_file(file_path, self.bucket_name, full_key, ExtraArgs=extra_args)

            public_url = f"{self.public_url}/{self.bucket_name}/{full_key}"
            logger.info(f"Uploaded file from path to S3: {full_key}")
            return public_url

        except ClientError as e:
            logger.error(f"Error uploading file from path to S3: {e}")
            raise

    def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        try:
            full_key = self._get_full_key(key)

            self.s3_client.delete_object(Bucket=self.bucket_name, Key=full_key)

            logger.info(f"Deleted file from S3: {full_key}")
            return True

        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False

    def cleanup_task_folder(self, task_id: str) -> bool:
        """Delete all files for a specific task from S3 (uses env base_folder)"""
        try:
            # List all objects with task_id prefix
            prefix = self._get_full_key(f"{task_id}/")

            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)

            if "Contents" not in response:
                logger.info(f"No files found for task {task_id} in S3")
                return True

            # Delete all objects in batches
            objects_to_delete = []
            for obj in response["Contents"]:
                objects_to_delete.append({"Key": obj["Key"]})

                # Delete in batches of 1000 (S3 limit)
                if len(objects_to_delete) >= 1000:
                    self._delete_objects_batch(objects_to_delete)
                    objects_to_delete = []

            # Delete remaining objects
            if objects_to_delete:
                self._delete_objects_batch(objects_to_delete)

            logger.info(f"Successfully cleaned up S3 folder for task {task_id}")
            return True

        except ClientError as e:
            logger.error(f"Error cleaning up S3 folder for task {task_id}: {e}")
            return False

    def cleanup_task_folder_with_base_path(self, task_id: str, base_path: str) -> bool:
        """Delete all files for a specific task from S3 with custom base_path"""
        try:
            # Construct prefix: base_path/task_id/
            if base_path:
                prefix = f"{base_path}/{task_id}/"
            else:
                prefix = f"{task_id}/"

            logger.info(f"Cleaning up S3 objects with prefix: {prefix}")

            # Use paginator to handle large number of objects
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            objects_deleted = 0
            for page in pages:
                if "Contents" not in page:
                    continue

                # Delete objects in batches
                objects_to_delete = []
                for obj in page["Contents"]:
                    objects_to_delete.append({"Key": obj["Key"]})

                    # Delete in batches of 1000 (S3 limit)
                    if len(objects_to_delete) >= 1000:
                        deleted_count = self._delete_objects_batch(objects_to_delete)
                        objects_deleted += deleted_count
                        objects_to_delete = []

                # Delete remaining objects
                if objects_to_delete:
                    deleted_count = self._delete_objects_batch(objects_to_delete)
                    objects_deleted += deleted_count

            if objects_deleted > 0:
                logger.info(
                    f"Successfully cleaned up {objects_deleted} S3 objects for task {task_id} in {prefix}"
                )
            else:
                logger.info(f"No files found for task {task_id} in S3 prefix: {prefix}")

            return True

        except ClientError as e:
            logger.error(
                f"Error cleaning up S3 folder for task {task_id} with base_path {base_path}: {e}"
            )
            return False

    def _delete_objects_batch(self, objects_to_delete):
        """Delete a batch of objects from S3"""
        if not objects_to_delete:
            return 0

        self.s3_client.delete_objects(
            Bucket=self.bucket_name, Delete={"Objects": objects_to_delete, "Quiet": True}
        )
        deleted_count = len(objects_to_delete)
        logger.info(f"Deleted batch of {deleted_count} objects from S3")
        return deleted_count

    def download_file_from_url(self, url: str, local_path: str) -> bool:
        """Download file from public URL using HTTP"""
        try:
            import time

            import requests

            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download with retries for large files
            max_retries = 3
            timeout = 300  # 5 minutes per request

            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Downloading from URL (attempt {
                        attempt + 1}): {url}"
                    )

                    response = requests.get(url, stream=True, timeout=timeout)
                    response.raise_for_status()

                    with open(local_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                    logger.info(f"Downloaded file from URL: {url} to {local_path}")
                    return True

                except Exception as e:
                    logger.warning(
                        f"Download attempt {
                        attempt + 1} failed: {e}"
                    )
                    if attempt < max_retries - 1:
                        delay = 2 * (2 ** attempt)  # 2s, 4s, 8s
                        logger.info(f"Waiting {delay} seconds before retry...")
                        time.sleep(delay)
                    else:
                        raise

        except Exception as e:
            logger.error(f"Error downloading file from URL: {e}")
            return False

    def download_file(
            self, bucket_name_or_key: str, key_or_local_path: str, local_path: str = None
    ) -> bool:
        """Download file from S3 to local path"""
        try:
            # Handle both signatures: download_file(key, local_path) and
            # download_file(bucket_name, key, local_path)
            if local_path is None:
                # Two parameter call: download_file(key, local_path)
                key = bucket_name_or_key
                local_path = key_or_local_path
                bucket_name = self.bucket_name
                full_key = self._get_full_key(key)
            else:
                # Three parameter call: download_file(bucket_name, key,
                # local_path)
                bucket_name = bucket_name_or_key
                key = key_or_local_path
                full_key = key  # Use key as-is when bucket is explicitly provided

            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Create clean client for download without extra headers
            from botocore.config import Config

            download_config = Config(
                retries={"max_attempts": 3, "mode": "adaptive"},
                read_timeout=900,
                connect_timeout=60,
                signature_version="s3v4",
            )

            download_client = boto3.client(
                "s3",
                endpoint_url=settings.aws_endpoint_url,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                config=download_config,
            )

            download_client.download_file(bucket_name, full_key, local_path)

            logger.info(f"Downloaded file from S3: {full_key} to {local_path}")
            return True

        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False

    def file_exists(self, key: str) -> bool:
        """Check if file exists in S3"""
        try:
            full_key = self._get_full_key(key)

            self.s3_client.head_object(Bucket=self.bucket_name, Key=full_key)
            return True

        except ClientError:
            return False

    def generate_output_key(
            self,
            task_id: str,
            profile_id: str,
            filename: str,
            s3_config: dict = None,
            prefix: str = None,
            face_type: str = None,
    ) -> str:
        """Generate output key based on folder structure config"""
        if s3_config is None:
            # Use default structure for backward compatibility
            if prefix:
                return f"{task_id}/{prefix}/{filename}"
            else:
                return f"{task_id}/{profile_id}/{filename}"

        # Handle face detection files with specific paths
        if face_type == "avatar":
            face_path = s3_config.get("face_avatar_path", "{task_id}/faces/avatars")
            folder_path = face_path.format(task_id=task_id, profile_id=profile_id)
        elif face_type == "image":
            face_path = s3_config.get("face_image_path", "{task_id}/faces/images")
            folder_path = face_path.format(task_id=task_id, profile_id=profile_id)
        else:
            # Handle profile outputs
            folder_structure = s3_config.get("folder_structure", "{task_id}/{profile_id}")
            folder_path = folder_structure.format(task_id=task_id, profile_id=profile_id)

        # Add base_path prefix if provided in config
        base_path = s3_config.get("base_path") if s3_config else None
        if base_path:
            return f"{base_path}/{folder_path}/{filename}"
        else:
            return f"{folder_path}/{filename}"

    def parse_s3_url(self, s3_url: str) -> tuple[str, str]:
        """Parse S3 URL and return bucket name and key"""
        if not s3_url.startswith("s3://"):
            raise ValueError(f"Invalid S3 URL: {s3_url}")

        # Remove s3:// prefix and split bucket and key
        url_without_prefix = s3_url[5:]
        parts = url_without_prefix.split("/", 1)

        if len(parts) < 2:
            raise ValueError(f"Invalid S3 URL format: {s3_url}")

        bucket_name = parts[0]
        key = parts[1]

        return bucket_name, key


s3_service = S3Service()
