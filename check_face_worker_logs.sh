#!/bin/bash

echo "🔍 Checking Face Detection Worker Logs and Status"
echo "================================================="

# SSH connection details
SSH_HOST="skl@192.168.0.234"
SSH_PORT="6789"
PROJECT_DIR="/home/skl/magic-transcode-media"

echo "📊 Checking container status..."
ssh -p $SSH_PORT $SSH_HOST "cd $PROJECT_DIR && docker ps -a | grep face-detection"

echo -e "\n🔄 Checking container restart count..."
ssh -p $SSH_PORT $SSH_HOST "cd $PROJECT_DIR && docker inspect transcode-face-detection-worker | grep -A 5 RestartCount"

echo -e "\n📝 Last 50 lines of container logs..."
ssh -p $SSH_PORT $SSH_HOST "cd $PROJECT_DIR && docker logs --tail 50 transcode-face-detection-worker"

echo -e "\n💾 Checking memory usage..."
ssh -p $SSH_PORT $SSH_HOST "cd $PROJECT_DIR && docker stats --no-stream transcode-face-detection-worker"

echo -e "\n🔍 Checking for OOM kills..."
ssh -p $SSH_PORT $SSH_HOST "dmesg | grep -i 'killed process' | tail -5"

echo -e "\n📋 Checking system logs for container events..."
ssh -p $SSH_PORT $SSH_HOST "journalctl -u docker -n 20 | grep face-detection"