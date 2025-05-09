import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any, Tuple
import mimetypes

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str,
                 region_name: str, bucket_name: str):
        """Initialize the S3 service with AWS credentials."""
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.bucket_name = bucket_name

        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )

        # Initialize S3 resource
        self.s3_resource = boto3.resource(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )

        # Ensure the bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure that the specified S3 bucket exists."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} exists and is accessible.")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.warning(f"Bucket {self.bucket_name} does not exist. Creating it...")
                try:
                    if self.region_name == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region_name}
                        )
                    logger.info(f"Bucket {self.bucket_name} created successfully.")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {str(create_error)}")
                    raise
            elif error_code == '403':
                logger.error(f"Access denied to bucket {self.bucket_name}. Check your AWS credentials.")
                raise
            else:
                logger.error(f"Error checking bucket: {str(e)}")
                raise

    def upload_file(self, file_path: str, s3_key: str, public: bool = False) -> Tuple[bool, str]:
        """
        Upload a file to S3 bucket.

        Args:
            file_path: Path to the local file
            s3_key: The key (path) in the S3 bucket
            public: Whether to make the file publicly accessible

        Returns:
            Tuple of (success, url_or_error_message)
        """
        try:
            # Determine file content type
            content_type, _ = mimetypes.guess_type(file_path)
            extra_args = {}

            if content_type:
                extra_args['ContentType'] = content_type

            if public:
                extra_args['ACL'] = 'public-read'

            # Upload the file
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            # Generate URL
            if public:
                url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            else:
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': s3_key},
                    ExpiresIn=3600  # URL valid for 1 hour
                )

            return True, url

        except Exception as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            return False, str(e)

    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download a file from S3 bucket.

        Args:
            s3_key: The key (path) in the S3 bucket
            local_path: Path to save the file locally

        Returns:
            bool: True if download was successful, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download the file
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            return True

        except Exception as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            return False

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3 bucket.

        Args:
            s3_key: The key (path) in the S3 bucket

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True

        except Exception as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            return False

    def delete_files(self, s3_keys: list) -> bool:
        """
        Delete multiple files from S3 bucket.

        Args:
            s3_keys: List of keys (paths) in the S3 bucket

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            objects = [{'Key': key} for key in s3_keys]
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects}
            )
            return True

        except Exception as e:
            logger.error(f"Error deleting files from S3: {str(e)}")
            return False

    def list_files(self, prefix: str = '') -> list:
        """
        List files in the S3 bucket with the given prefix.

        Args:
            prefix: The prefix to filter objects by

        Returns:
            list: List of dict with keys 'Key', 'LastModified', 'Size', 'ETag'
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')

            result = []
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        result.append({
                            'key': obj['Key'],
                            'last_modified': obj['LastModified'],
                            'size': obj['Size'],
                            'etag': obj['ETag']
                        })

            return result

        except Exception as e:
            logger.error(f"Error listing files in S3: {str(e)}")
            return []

    def get_file_url(self, s3_key: str, public: bool = False, expiration: int = 3600) -> str:
        """
        Get URL for a file in S3.

        Args:
            s3_key: The key (path) in the S3 bucket
            public: Whether the file is publicly accessible
            expiration: Time in seconds the presigned URL is valid (for non-public files)

        Returns:
            str: URL for the file
        """
        try:
            if public:
                return f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            else:
                return self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': s3_key},
                    ExpiresIn=expiration
                )

        except Exception as e:
            logger.error(f"Error generating URL for S3 file: {str(e)}")
            return ""

    def check_file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in the S3 bucket.

        Args:
            s3_key: The key (path) in the S3 bucket

        Returns:
            bool: True if the file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking if file exists in S3: {str(e)}")
                raise