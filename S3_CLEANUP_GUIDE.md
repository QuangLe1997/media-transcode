# S3 Deep Clean Guide

## Overview
This script safely removes the `dev-facefusion-media/transcode-service` folder and all its contents from S3.

## Safety Features
- **Triple confirmation** required before deletion
- **Dry run mode** to preview what would be deleted
- **Batch processing** to handle large folders
- **Detailed logging** with timestamps
- **Error handling** and rollback protection
- **Statistics** showing file counts and sizes

## Usage

### 1. Preview what would be deleted (DRY RUN)
```bash
python s3_deep_clean.py --folder "dev-facefusion-media/transcode-service" --dry-run
```

### 2. Perform actual deletion
```bash
python s3_deep_clean.py --folder "dev-facefusion-media/transcode-service"
```

### 3. Force deletion (skip confirmations) - DANGEROUS!
```bash
python s3_deep_clean.py --folder "dev-facefusion-media/transcode-service" --force
```

## Example Output

### Dry Run Preview:
```
🔍 Scanning folder: dev-facefusion-media/transcode-service/
🔍 DRY RUN - Preview of what would be deleted:
📁 Folder: dev-facefusion-media/transcode-service/
📊 Files: 1,234
💾 Size: 2.45 GB

📋 File breakdown:
   .mp4: 456 files (1.89 GB)
   .jpg: 778 files (456.78 MB)
   .json: 12 files (34.56 KB)
```

### Actual Deletion:
```
🚨 DANGER: You are about to DELETE the following S3 folder:
📁 Bucket: your-bucket-name
📂 Folder: dev-facefusion-media/transcode-service/
📊 Total Files: 1,234
💾 Total Size: 2.45 GB

⚠️  WARNING: This action CANNOT be undone!

Are you absolutely sure you want to delete this folder? (yes/no): yes
This will permanently delete ALL files. Type 'DELETE' to confirm: DELETE
Final confirmation - type the folder name 'dev-facefusion-media/transcode-service/' to proceed: dev-facefusion-media/transcode-service/

✅ Deletion confirmed. Proceeding...
🗑️  Deleting 1,234 objects...
✅ Deletion completed!
⏱️  Duration: 0:00:45.123456
✅ Successfully deleted: 1,234 objects
```

## Safety Measures

1. **Multiple Confirmations**: Requires 3 different confirmation inputs
2. **Folder Name Verification**: Must type exact folder name to proceed
3. **Dry Run First**: Always run with `--dry-run` first to preview
4. **Logging**: All operations logged to timestamped log file
5. **Batch Processing**: Handles large folders without memory issues
6. **Error Handling**: Graceful handling of S3 errors

## What Gets Deleted

All files and folders under the specified prefix, including:
- Video files (.mp4, .avi, .mov, etc.)
- Image files (.jpg, .png, .gif, etc.)
- Face detection avatars and images
- Metadata files (.json, .txt, etc.)
- Any other files in the folder

## Troubleshooting

### Error: AWS credentials not found
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

### Error: Connection timeout
- Check S3 endpoint URL in .env file
- Verify network connectivity
- Try smaller batch sizes

### Error: Permission denied
- Verify S3 bucket permissions
- Check IAM user has delete permissions
- Ensure correct bucket name

## Recovery
⚠️ **IMPORTANT**: There is NO recovery once files are deleted. Make sure you have backups if needed.

## Log Files
All operations are logged to files named:
- `s3_cleanup_YYYYMMDD_HHMMSS.log`

Check these files for detailed operation history and any errors.