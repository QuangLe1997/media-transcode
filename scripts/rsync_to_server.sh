#!/bin/bash

# Rsync script to sync changed files to server
# Usage: ./rsync_to_server.sh

set -e  # Exit on any error

SERVER="192.168.0.234"
SERVER_USER="quang"
SERVER_PATH="/quang/quang/media-transcode"
LOCAL_PATH="/Users/quang/Documents/skl-workspace/transcode/media-transcode"

echo "📡 Rsync to Server: $SERVER_USER@$SERVER:$SERVER_PATH"
echo "=========================================="

# Check if server is reachable
echo "🔍 Testing connection..."
if ! ping -c 1 -W 3 $SERVER > /dev/null 2>&1; then
    echo "❌ Cannot reach server $SERVER"
    exit 1
fi

echo "✅ Server is reachable"

# Files and directories to sync
SYNC_PATHS=(
    "src/transcode_service/services/s3_service.py"
    "src/transcode_service/api/main.py" 
    "src/transcode_service/core/"
    "src/transcode_service/models/"
    "config/api_compatible_templates.json"
    "scripts/"
    "requirements.txt"
    "pyproject.toml"
)

echo ""
echo "📁 Syncing files and directories..."

for path in "${SYNC_PATHS[@]}"; do
    if [ -e "$LOCAL_PATH/$path" ]; then
        echo "   → Syncing: $path"
        
        # Create parent directory on server if needed
        parent_dir=$(dirname "$SERVER_PATH/$path")
        ssh "$SERVER_USER@$SERVER" "mkdir -p '$parent_dir'" 2>/dev/null || true
        
        # Sync with rsync
        rsync -avz --progress \
            "$LOCAL_PATH/$path" \
            "$SERVER_USER@$SERVER:$SERVER_PATH/$path"
    else
        echo "   ⚠️  Skipping (not found): $path"
    fi
done

echo ""
echo "✅ Files synced successfully!"

# Now SSH to server and build
echo ""
echo "🔧 Building and restarting on server..."

ssh "$SERVER_USER@$SERVER" << EOF
    set -e
    cd "$SERVER_PATH"
    
    echo "📍 Current directory: \$(pwd)"
    echo "📋 Checking synced files..."
    
    # Check if S3 fix is present
    if grep -q "AcceptRanges.*automatically set by S3" src/transcode_service/services/s3_service.py; then
        echo "✅ S3 fix detected in synced file"
    else
        echo "⚠️  S3 fix may not be present"
    fi
    
    # Install/update dependencies if requirements changed
    if [ -f "requirements.txt" ]; then
        echo "📦 Updating Python dependencies..."
        pip install -r requirements.txt --quiet || echo "⚠️  pip install had issues"
    fi
    
    # Check what services are running
    echo ""
    echo "🔍 Checking running services..."
    
    # Check Docker
    if command -v docker-compose &> /dev/null && [ -f "docker-compose.yml" ]; then
        echo "🐳 Found Docker Compose - restarting services..."
        docker-compose down || true
        sleep 2
        docker-compose up -d --build
        sleep 5
        
        echo "📊 Docker services status:"
        docker-compose ps
        
    # Check systemd services
    elif systemctl list-unit-files | grep -q transcode; then
        echo "⚙️  Found systemd services - restarting..."
        sudo systemctl restart transcode-* || true
        sleep 3
        
        echo "📊 Service status:"
        systemctl status transcode-* --no-pager -l || true
        
    # Check PM2
    elif command -v pm2 &> /dev/null; then
        echo "🔧 Found PM2 - restarting processes..."
        pm2 restart all || pm2 start ecosystem.config.js || true
        sleep 3
        
        echo "📊 PM2 status:"
        pm2 status
        
    else
        echo "⚠️  No known process manager found"
        echo "💡 Please manually restart the API services"
    fi
    
    echo ""
    echo "🌐 Testing API endpoint..."
    sleep 3
    
    # Test API
    if curl -s -f http://localhost:8087/config-templates > /dev/null; then
        echo "✅ API is responding on port 8087"
        curl -s http://localhost:8087/config-templates | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'📊 Found {data.get(\"count\", 0)} config templates')
except:
    print('📊 API responding but JSON parsing failed')
"
    else
        echo "❌ API not responding on port 8087"
    fi
    
EOF

echo ""
echo "✅ Rsync and rebuild completed!"
echo ""
echo "🧪 Ready for testing:"
echo "   python scripts/test_remote_server.py"