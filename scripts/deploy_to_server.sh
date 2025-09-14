#!/bin/bash

# Deploy script to sync code to server via SSH
# Usage: ./deploy_to_server.sh

set -e  # Exit on any error

SERVER_IP="192.168.0.234"
SERVER_USER="root"  # Adjust as needed
SERVER_PATH="/opt/transcode/media-transcode"  # Adjust as needed
LOCAL_PATH="/Users/quang/Documents/skl-workspace/transcode/media-transcode"

echo "🚀 Deploying to Server: $SERVER_IP"
echo "=========================================="

# Step 1: Sync the fixed file
echo "📁 Syncing S3 service fix..."
scp "$LOCAL_PATH/src/transcode_service/services/s3_service.py" \
    "$SERVER_USER@$SERVER_IP:$SERVER_PATH/src/transcode_service/services/s3_service.py"

echo "✅ File synced successfully"

# Step 2: SSH to server and restart services
echo ""
echo "🔄 Restarting services on server..."

ssh "$SERVER_USER@$SERVER_IP" << 'EOF'
    cd /opt/transcode/media-transcode
    
    echo "📍 Current directory: $(pwd)"
    
    # Check if using Docker
    if [ -f "docker-compose.yml" ]; then
        echo "🐳 Restarting Docker services..."
        docker-compose restart api
        sleep 5
        
        echo "📊 Checking Docker status..."
        docker-compose ps
        
    # Check if using systemd
    elif systemctl is-active --quiet transcode-api; then
        echo "⚙️  Restarting systemd service..."
        systemctl restart transcode-api
        sleep 3
        
        echo "📊 Checking service status..."
        systemctl status transcode-api --no-pager -l
        
    # Check if using PM2
    elif command -v pm2 &> /dev/null; then
        echo "🔧 Restarting PM2 process..."
        pm2 restart transcode-api
        sleep 3
        
        echo "📊 Checking PM2 status..."
        pm2 status
        
    else
        echo "⚠️  No known process manager found"
        echo "💡 Please manually restart the API service"
    fi
    
    echo ""
    echo "🌐 Testing API endpoint..."
    curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8087/config-templates || echo "❌ API not responding"
    
EOF

echo ""
echo "✅ Deployment completed!"
echo "🧪 Ready for testing..."