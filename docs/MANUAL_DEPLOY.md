# 🚀 Manual Deployment Instructions

## ❌ SSH Connection Issue
SSH connection to server `quang@192.168.0.234` is being refused. Here are manual deployment options:

## 📋 What Needs to be Deployed

**Main Fix**: `src/transcode_service/services/s3_service.py`
- **Problem**: Lines with `extra_args["AcceptRanges"] = "bytes"`  
- **Solution**: Remove those lines (they're invalid S3 parameters)

## 🔧 Manual Deployment Options

### Option 1: Direct File Edit on Server
```bash
# SSH to server (adjust user/port as needed)
ssh quang@192.168.0.234
# or try: ssh -p 2222 quang@192.168.0.234
# or try: ssh root@192.168.0.234

# Navigate to project
cd /quang/quang/media-transcode

# Edit the file
nano src/transcode_service/services/s3_service.py

# Find and REMOVE these 2 lines:
#   Line ~116: extra_args["AcceptRanges"] = "bytes"  
#   Line ~172: extra_args["AcceptRanges"] = "bytes"

# Save and restart service
```

### Option 2: Copy Fixed File
If you have file access (FTP/SFTP/Panel):

**Source File**: `src/transcode_service/services/s3_service.py` (from this local project)
**Target Path**: `/quang/quang/media-transcode/src/transcode_service/services/s3_service.py`

### Option 3: HTTP File Server
```bash
# From local machine - serve the fixed file
cd src/transcode_service/services/
python3 -m http.server 8080

# From server - download the fixed file  
curl -o s3_service.py http://YOUR_LOCAL_IP:8080/s3_service.py
mv s3_service.py /quang/quang/media-transcode/src/transcode_service/services/s3_service.py
```

## 🔄 Restart Services on Server

After deploying the fix:

```bash
cd /quang/quang/media-transcode

# Option 1: Docker Compose
docker-compose restart api
docker-compose ps

# Option 2: Systemd
sudo systemctl restart transcode-api
systemctl status transcode-api

# Option 3: PM2
pm2 restart transcode-api
pm2 status

# Option 4: Manual process restart
# Kill current process and restart
pkill -f "uvicorn.*transcode"
# Then start again with your usual command
```

## 🧪 Test After Deploy

```bash
# Test API endpoint
curl http://192.168.0.234:8087/config-templates

# Should return JSON with templates (not 500 error)
```

## 📝 Verification

After restart, the S3 upload error should be gone:
- ❌ Before: `{"detail":"Invalid extra_args key 'AcceptRanges'..."`
- ✅ After: Transcode tasks complete successfully

## 🆘 If Still Having Issues

1. **Check logs**: Look for Docker/systemd/application logs
2. **Verify fix**: Confirm `AcceptRanges` lines were removed
3. **Port check**: Ensure API is running on port 8087
4. **Dependencies**: Run `pip install -r requirements.txt` if needed

---

**The fix is simple but critical - just remove those 2 `AcceptRanges` lines and restart! 🎯**