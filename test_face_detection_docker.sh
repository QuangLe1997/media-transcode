#!/bin/bash

echo "🧪 Testing Face Detection Worker in Docker"
echo "=" * 50

# Setup models directory
echo "🔧 Setting up models directory..."
./setup_models_dir.sh

# Build and run face detection worker
echo "🏗️ Building Docker image..."
docker build -t transcode-face-detection-test -f Dockerfile .

echo "🚀 Running face detection worker test..."
docker run --rm \
    -v $(pwd)/models_faces:/app/models_faces \
    -v $(pwd)/logs:/app/logs \
    -e PYTHONUNBUFFERED=1 \
    transcode-face-detection-test \
    python -c "
import sys
sys.path.append('/app')
from services.model_downloader import ensure_face_detection_models
import os

print('🔍 Testing model download...')
models_dir = '/app/models_faces'
print(f'📁 Models directory: {models_dir}')
print(f'📊 Directory exists: {os.path.exists(models_dir)}')
print(f'📝 Directory writable: {os.access(models_dir, os.W_OK)}')

print('📥 Downloading models...')
success = ensure_face_detection_models(models_dir)
print(f'✅ Download success: {success}')

print('📋 Directory contents:')
for file in os.listdir(models_dir):
    filepath = os.path.join(models_dir, file)
    size = os.path.getsize(filepath)
    print(f'  {file}: {size:,} bytes')
"

echo "✅ Face detection worker test completed!"