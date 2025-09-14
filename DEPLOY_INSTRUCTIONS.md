# 🚀 Deploy S3 Fix to Server

## ✅ Status
- **Local Fix**: ✅ COMPLETED and TESTED
- **Remote Server**: ❌ NEEDS FIX (still has AcceptRanges error)

## 🔧 Quick Deploy Commands

### Option 1: Direct File Copy (Recommended)
```bash
# Copy the fixed file to server
scp src/transcode_service/services/s3_service.py root@192.168.0.234:/opt/transcode/media-transcode/src/transcode_service/services/s3_service.py

# SSH to server and restart
ssh root@192.168.0.234

# On server - restart the API service:
cd /opt/transcode/media-transcode

# If using Docker:
docker-compose restart api

# OR if using systemd:
sudo systemctl restart transcode-api

# OR if using PM2:
pm2 restart transcode-api
```

### Option 2: Use Provided Script
```bash
# Run the sync script
./scripts/sync_s3_fix.sh root@192.168.0.234 /opt/transcode/media-transcode

# Then SSH and restart as above
```

## 🧪 Test After Deploy

```bash
# Test if server is fixed
python scripts/test_remote_server.py

# Should show:
# ✅ Task created successfully!
# ✅ Remote server test PASSED!
```

## 📋 What Was Fixed

**File**: `src/transcode_service/services/s3_service.py`

**Lines 116 & 172** - Removed invalid parameter:
```python
# OLD (BROKEN):
extra_args["AcceptRanges"] = "bytes"

# NEW (FIXED):
# Note: AcceptRanges header is automatically set by S3 for video streaming
```

**Root Cause**: `AcceptRanges` is not a valid S3 `ExtraArgs` parameter. It's an HTTP response header that S3 sets automatically.

## 🎯 Expected Results After Fix

1. ✅ No more 500 errors on file uploads
2. ✅ API server won't crash during transcode
3. ✅ S3 uploads will work properly
4. ✅ Transcode tasks will complete successfully

## 📞 Need Help?

If you encounter issues during deployment:

1. **Check SSH connection**: `ssh root@192.168.0.234`
2. **Verify file paths**: Make sure server paths are correct
3. **Check service status**: `systemctl status transcode-api` or `docker-compose ps`
4. **View logs**: `docker logs container-name` or `journalctl -u transcode-api`

---

**🎉 Ready to deploy! The fix is confirmed working locally.**