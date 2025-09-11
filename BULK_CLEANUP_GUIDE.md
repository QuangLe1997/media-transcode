# S3 Bulk Cleanup Guide

## 🚀 Quick Usage (Single Confirmation)

### Option 1: One-liner cleanup (Recommended)
```bash
python quick_clean.py
```
**Cleans all common old folders with just one confirmation!**

### Option 2: Custom folders
```bash
python s3_bulk_clean.py --folders "transcode-service" "old-data" "temp-files"
```

### Option 3: Preview first (Safe)
```bash
python s3_bulk_clean.py --folders "transcode-service" "old-data" --dry-run
```

## 📋 What Gets Cleaned

### Default folders in `quick_clean.py`:
- `dev-facefusion-media/transcode-service`
- `transcode-service`
- `old-transcode-outputs`
- `temp-uploads`
- `test-outputs`
- `face-detection-temp`
- `legacy-outputs`

## 🔥 Example Usage

### Quick cleanup (single command):
```bash
python quick_clean.py
```

**Output:**
```
🧹 Quick S3 Cleanup
📁 Will scan these folders:
   - dev-facefusion-media/transcode-service
   - transcode-service
   - old-transcode-outputs
   - temp-uploads

🔍 Scanning folders...
✅ transcode-service: 1,234 files (2.45 GB)
⚪ old-transcode-outputs: empty
⚪ temp-uploads: empty

📊 BULK DELETION SUMMARY:
📁 Folders to delete: 1
📄 Total files: 1,234
💾 Total size: 2.45 GB

🚨 WARNING: BULK DELETION
📊 Total files to delete: 1,234
💾 Total size: 2.45 GB
⚠️  This action CANNOT be undone!

Type 'DELETE ALL' to confirm bulk deletion: DELETE ALL

✅ Bulk deletion confirmed!
🗑️  Starting bulk deletion of 1,234 objects...
🗑️  Batch 1/2 (50.0%): deleted 1000 objects
🗑️  Batch 2/2 (100.0%): deleted 234 objects

✅ Bulk deletion completed!
⏱️  Duration: 0:00:15.123456
✅ Successfully deleted: 1,234 objects
```

### Custom folders:
```bash
python s3_bulk_clean.py --folders "folder1" "folder2" "folder3"
```

### With common patterns:
```bash
python s3_bulk_clean.py --folders "my-custom-folder" --common-patterns
```

## 🛡️ Safety Features

- **Single confirmation** - Just type 'DELETE ALL' once
- **Concurrent scanning** - Fast folder scanning with thread pool
- **Batch deletion** - Efficient S3 batch operations
- **Progress tracking** - Real-time deletion progress
- **Error handling** - Graceful handling of S3 errors
- **Dry run mode** - Preview before deletion
- **Detailed logging** - All operations logged

## 📊 Performance

- **Concurrent scanning** - Up to 10 folders scanned simultaneously
- **Batch operations** - Delete up to 1,000 objects per S3 call
- **Progress tracking** - Real-time updates during deletion
- **Memory efficient** - Handles large folders without memory issues

## 🔧 Advanced Options

### Scan specific folders:
```bash
python s3_bulk_clean.py --folders "transcode-service" "old-data" "temp-*"
```

### Preview only:
```bash
python s3_bulk_clean.py --folders "transcode-service" --dry-run
```

### Include common patterns:
```bash
python s3_bulk_clean.py --folders "my-folder" --common-patterns
```

## 🚨 Important Notes

1. **Single confirmation** - Only need to type 'DELETE ALL' once
2. **Bulk operation** - Processes multiple folders at once
3. **No recovery** - Deleted files cannot be recovered
4. **Concurrent processing** - Much faster than single folder cleanup
5. **Automatic filtering** - Empty folders are automatically skipped

## 💡 Tips

1. **Always preview first** with `--dry-run`
2. **Use quick_clean.py** for routine cleanup
3. **Check logs** for detailed operation history
4. **Monitor progress** during large deletions
5. **Cancel anytime** with Ctrl+C

## 📝 Log Files

All operations are logged to:
- `s3_bulk_cleanup_YYYYMMDD_HHMMSS.log`

## 🎯 Common Use Cases

### Routine cleanup:
```bash
python quick_clean.py
```

### Project cleanup:
```bash
python s3_bulk_clean.py --folders "project1" "project2" "project3"
```

### Development cleanup:
```bash
python s3_bulk_clean.py --folders "dev-*" "test-*" "temp-*"
```

This bulk cleanup system makes it easy to clean multiple S3 folders with just one confirmation, saving time and reducing repetitive actions!