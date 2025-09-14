# Sync Code to Server Instructions

## 1. Push Local Changes to Git Repository

```bash
# Check current status
git status

# Push to remote repository (adjust branch/remote as needed)
git push origin master
```

## 2. On Server (192.168.0.234)

### Option A: Pull from Git Repository
```bash
# SSH to server
ssh user@192.168.0.234

# Navigate to project directory
cd /path/to/transcode/media-transcode

# Pull latest changes
git pull origin master

# Restart services
sudo systemctl restart transcode-api
# or
docker-compose restart
# or
pm2 restart transcode-api
```

### Option B: Direct File Copy (if no git on server)
```bash
# From local machine, copy the fixed file
scp src/transcode_service/services/s3_service.py user@192.168.0.234:/path/to/transcode/media-transcode/src/transcode_service/services/s3_service.py

# SSH to server and restart
ssh user@192.168.0.234
sudo systemctl restart transcode-api
```

## 3. Verify Server Restart

```bash
# Check if API is running on server
curl -X GET http://192.168.0.234:8087/config-templates

# Check Docker logs if using Docker
docker logs transcode-api-container

# Check service status
sudo systemctl status transcode-api
```

## 4. Test the Fix

Run the test script against server:

```bash
# Update test script to use server URL
python scripts/test_s3_fix.py
```

## Key Changes Made

- **File**: `src/transcode_service/services/s3_service.py`
- **Fix**: Removed invalid `AcceptRanges` parameter from S3 upload
- **Lines**: 116 and 172 (removed `extra_args["AcceptRanges"] = "bytes"`)
- **Reason**: AcceptRanges is not a valid S3 ExtraArgs parameter - it's automatically set by S3

## Expected Result

- ✅ No more S3 upload errors
- ✅ API server won't crash on video uploads
- ✅ Transcode tasks will process successfully