#!/bin/bash

# Simple script to sync S3 fix to server
# Usage: ./sync_s3_fix.sh [user@server] [remote_path]

SERVER_ADDRESS="${1:-root@192.168.0.234}"
REMOTE_PATH="${2:-/opt/transcode/media-transcode}"
LOCAL_FILE="src/transcode_service/services/s3_service.py"

echo "🔧 Syncing S3 Fix to Server"
echo "============================="
echo "Server: $SERVER_ADDRESS" 
echo "Remote Path: $REMOTE_PATH"
echo "File: $LOCAL_FILE"
echo ""

# Check if local file exists
if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ Local file not found: $LOCAL_FILE"
    exit 1
fi

echo "📁 Copying file to server..."
scp "$LOCAL_FILE" "$SERVER_ADDRESS:$REMOTE_PATH/$LOCAL_FILE"

if [ $? -eq 0 ]; then
    echo "✅ File copied successfully!"
    echo ""
    echo "🔄 Now SSH to server and restart the API service:"
    echo "   ssh $SERVER_ADDRESS"
    echo "   cd $REMOTE_PATH"
    echo "   # Restart your API service (docker-compose/systemd/pm2)"
    echo ""
    echo "🧪 Then test with:"
    echo "   curl http://192.168.0.234:8087/config-templates"
else
    echo "❌ File copy failed!"
    exit 1
fi