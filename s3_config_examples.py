#!/usr/bin/env python3
"""
Examples of enhanced S3OutputConfig usage with message fallbacks
"""

from models.schemas import S3OutputConfig
from config import settings

# Example 1: Minimal message - all fields use defaults from environment
minimal_message_s3_config = {
    "base_path": "my-custom-outputs"
}

enhanced_config = S3OutputConfig.with_defaults(minimal_message_s3_config, settings)
print("=== Minimal Config Example ===")
print(f"Bucket: {enhanced_config.bucket}")  # From settings.aws_bucket_name
print(f"Base path: {enhanced_config.base_path}")  # From message
print(f"Cleanup on reset: {enhanced_config.cleanup_on_task_reset}")  # Default True
print(f"AWS endpoint: {enhanced_config.aws_endpoint_url}")  # From settings
print()

# Example 2: Full override message - uses message values over defaults
full_override_message = {
    "base_path": "special-project-outputs",
    "folder_structure": "custom/{task_id}/results/{profile_id}",
    "bucket": "special-bucket",
    "aws_endpoint_url": "https://custom-s3.example.com",
    "cleanup_on_task_reset": False,
    "cleanup_temp_files": False,
    "upload_timeout": 1800,  # 30 minutes
    "max_retries": 5
}

enhanced_config_full = S3OutputConfig.with_defaults(full_override_message, settings)
print("=== Full Override Example ===")
print(f"Bucket: {enhanced_config_full.bucket}")  # From message
print(f"Folder structure: {enhanced_config_full.folder_structure}")  # From message
print(f"Cleanup on reset: {enhanced_config_full.cleanup_on_task_reset}")  # From message (False)
print(f"Upload timeout: {enhanced_config_full.upload_timeout}")  # From message (1800)
print(f"AWS endpoint: {enhanced_config_full.aws_endpoint_url}")  # From message
print()

# Example 3: Mixed config - some from message, some from defaults
mixed_message = {
    "base_path": "hybrid-outputs",
    "cleanup_failed_outputs": True,  # Override default False
    "max_retries": 1  # Override default 3
    # bucket, aws_endpoint_url, etc. will come from settings
}

enhanced_config_mixed = S3OutputConfig.with_defaults(mixed_message, settings)
print("=== Mixed Config Example ===")
print(f"Bucket: {enhanced_config_mixed.bucket}")  # From settings
print(f"Base path: {enhanced_config_mixed.base_path}")  # From message
print(f"Cleanup failed outputs: {enhanced_config_mixed.cleanup_failed_outputs}")  # From message (True)
print(f"Max retries: {enhanced_config_mixed.max_retries}")  # From message (1)
print(f"Cleanup temp files: {enhanced_config_mixed.cleanup_temp_files}")  # Default (True)
print()

# Example 4: Empty message - all defaults
empty_message = {}
enhanced_config_empty = S3OutputConfig.with_defaults(empty_message, settings)
print("=== All Defaults Example ===")
print(f"Base path: {enhanced_config_empty.base_path}")  # Default 'transcode-outputs'
print(f"Folder structure: {enhanced_config_empty.folder_structure}")  # Default template
print(f"Cleanup on reset: {enhanced_config_empty.cleanup_on_task_reset}")  # Default True
print(f"Upload timeout: {enhanced_config_empty.upload_timeout}")  # Default 900