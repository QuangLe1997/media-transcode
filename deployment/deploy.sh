#!/bin/bash

# Deployment script for production server with GPU

# Build and push image
echo "Building Docker image..."
docker build -t ${DOCKER_REGISTRY_HOST}/${IMAGE_NAME}:${IMAGE_TAG} .

echo "Pushing image to registry..."
docker push ${DOCKER_REGISTRY_HOST}/${IMAGE_NAME}:${IMAGE_TAG}

# Deploy to server
echo "Deploying to server..."
ssh skl@192.168.0.234 -p 6789 << 'EOF'
cd /path/to/magic-transcode-media

# Pull latest image
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Restart services with GPU enabled
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Check logs
docker-compose logs -f face-detection-worker | grep -E "(CUDA|GPU)" | head -20
EOF