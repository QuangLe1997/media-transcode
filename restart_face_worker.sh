#!/bin/bash

echo "🔄 Restarting Face Detection Worker"
echo "==================================="

# SSH connection details
SSH_HOST="skl@192.168.0.234"
SSH_PORT="6789"
PROJECT_DIR="/home/skl/magic-transcode-media"

echo "📋 Copying updated files to server..."
scp -P $SSH_PORT docker-compose.yml services/face_detect_service.py $SSH_HOST:$PROJECT_DIR/

echo -e "\n🛑 Stopping face detection worker..."
ssh -p $SSH_PORT $SSH_HOST "cd $PROJECT_DIR && docker-compose stop face-detection-worker"

echo -e "\n🗑️ Removing old container..."
ssh -p $SSH_PORT $SSH_HOST "cd $PROJECT_DIR && docker-compose rm -f face-detection-worker"

echo -e "\n🚀 Starting face detection worker with new config..."
ssh -p $SSH_PORT $SSH_HOST "cd $PROJECT_DIR && docker-compose up -d face-detection-worker"

echo -e "\n⏳ Waiting for worker to start..."
sleep 10

echo -e "\n📊 Checking new container status..."
ssh -p $SSH_PORT $SSH_HOST "cd $PROJECT_DIR && docker ps | grep face-detection"

echo -e "\n📝 Showing initial logs..."
ssh -p $SSH_PORT $SSH_HOST "cd $PROJECT_DIR && docker logs --tail 30 transcode-face-detection-worker"

echo -e "\n✅ Face detection worker restarted!"