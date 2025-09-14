#!/bin/bash

# Simple rsync script - adjust SSH settings as needed
# Usage: ./simple_rsync.sh [ssh_port]

SERVER="192.168.0.234"
SERVER_USER="skl"
SERVER_PATH="/quang/quang/media-transcode"
LOCAL_PATH="/Users/quang/Documents/skl-workspace/transcode/media-transcode"
SSH_PORT="${1:-6789}"

echo "📡 Rsync to Server (Port: $SSH_PORT)"
echo "======================================"
echo "Target: $SERVER_USER@$SERVER:$SERVER_PATH"
echo ""

# Test different SSH configurations
echo "🔍 Testing SSH connection..."

# Try default SSH port
if ssh -o ConnectTimeout=5 -o BatchMode=yes -p $SSH_PORT "$SERVER_USER@$SERVER" "echo 'SSH OK'" 2>/dev/null; then
    echo "✅ SSH connection successful on port $SSH_PORT"
    SSH_OPTS="-e ssh -p $SSH_PORT"
else
    echo "❌ SSH connection failed on port $SSH_PORT"
    echo ""
    echo "💡 Possible solutions:"
    echo "   1. Try different SSH port: ./simple_rsync.sh 2222"
    echo "   2. Check SSH key: ssh-add ~/.ssh/id_rsa"
    echo "   3. Try with password: ssh $SERVER_USER@$SERVER"
    echo "   4. Use manual scp instead:"
    echo "      scp src/transcode_service/services/s3_service.py $SERVER_USER@$SERVER:$SERVER_PATH/src/transcode_service/services/s3_service.py"
    exit 1
fi

echo ""
echo "📁 Syncing critical files..."

# Sync only the most important files first
CRITICAL_FILES=(
    "src/transcode_service/services/s3_service.py"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$LOCAL_PATH/$file" ]; then
        echo "   → $file"
        rsync -avz -e "ssh -p $SSH_PORT" \
            "$LOCAL_PATH/$file" \
            "$SERVER_USER@$SERVER:$SERVER_PATH/$file"
    fi
done

echo ""
echo "✅ Critical files synced!"
echo ""
echo "🔧 Now restart the server manually:"
echo "   ssh -p $SSH_PORT $SERVER_USER@$SERVER"
echo "   cd $SERVER_PATH"
echo "   # Restart your API service"
echo ""
echo "🧪 Then test:"
echo "   curl http://$SERVER:8087/config-templates"