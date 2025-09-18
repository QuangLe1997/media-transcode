#!/bin/bash

# Manual stop script for PRODUCTION server
# Stops all running containers on the production environment

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVER="54.248.140.63"
USER="quanglv"

echo -e "${BLUE}=== Manual Stop Deployment on PRODUCTION Server $SERVER ===${NC}"
echo

echo -e "${YELLOW}📡 Testing server connectivity...${NC}"
if ping -c 1 $SERVER &> /dev/null; then
    echo -e "${GREEN}✅ Server is reachable${NC}"
else
    echo -e "${RED}❌ Server is not reachable${NC}"
    exit 1
fi

echo -e "${YELLOW}🛑 Stopping containers on PRODUCTION server...${NC}"

# SSH into server and stop containers
ssh $USER@$SERVER << 'ENDSSH'
set -e

echo "📂 Navigating to project directory..."
cd /quang/quang/media-transcode

echo "📂 Navigating to deployment directory..."
cd deployment

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ] && [ ! -f "docker-compose.yaml" ]; then
    echo "⚠️  No docker-compose.yml found in /quang/quang/media-transcode/deployment"
    echo "⚠️  Project may not be deployed yet or in different location"
    exit 0
fi

echo "🛑 Stopping media-transcode containers..."
docker-compose down --remove-orphans

echo "📊 Media-transcode containers stopped:"
docker-compose ps

echo "✅ PRODUCTION server containers stopped successfully!"
ENDSSH

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Successfully stopped all containers on PRODUCTION server${NC}"
    echo -e "${GREEN}🎉 PRODUCTION environment is now stopped${NC}"
else
    echo -e "${RED}❌ Failed to stop containers on PRODUCTION server${NC}"
    exit 1
fi

echo
echo -e "${BLUE}=== Stop operation completed ===${NC}"