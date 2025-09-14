#!/bin/bash

# Deploy script for media-transcode service
# This script should be run on the deployment server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$HOME/media-transcode"
DEPLOYMENT_DIR="$PROJECT_DIR/deployment"
BACKUP_DIR="$HOME/backups/media-transcode"

echo -e "${GREEN}Starting deployment of media-transcode service...${NC}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Navigate to project directory
cd "$PROJECT_DIR"

# Pull latest code from git
echo -e "${YELLOW}Pulling latest code from git...${NC}"
git pull origin master

# Check if .env file exists
if [ ! -f "$DEPLOYMENT_DIR/.env" ]; then
    echo -e "${RED}Error: .env file not found in deployment directory${NC}"
    echo "Please create $DEPLOYMENT_DIR/.env with required environment variables"
    exit 1
fi

# Check if key.json exists
if [ ! -f "$PROJECT_DIR/src/transcode_service/key.json" ]; then
    echo -e "${YELLOW}Warning: Google Cloud key.json not found${NC}"
    echo "Some features may not work without proper GCP credentials"
fi

# Navigate to deployment directory
cd "$DEPLOYMENT_DIR"

# Backup current database
echo -e "${YELLOW}Backing up database...${NC}"
BACKUP_FILE="$BACKUP_DIR/postgres_backup_$(date +%Y%m%d_%H%M%S).sql"
docker-compose exec -T postgres pg_dump -U transcode_user transcode_db > "$BACKUP_FILE" 2>/dev/null || echo "No existing database to backup"

# Build new images
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose build --no-cache

# Stop current containers
echo -e "${YELLOW}Stopping current containers...${NC}"
docker-compose down

# Start new containers
echo -e "${YELLOW}Starting new containers...${NC}"
docker-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 15

# Health check
echo -e "${YELLOW}Running health checks...${NC}"

# Check postgres
if docker-compose exec -T postgres pg_isready -U transcode_user -d transcode_db; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not ready${NC}"
fi

# Check API
if curl -f http://localhost:8087/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}✗ API health check failed${NC}"
fi

# Check frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is accessible${NC}"
else
    echo -e "${RED}✗ Frontend is not accessible${NC}"
fi

# Show running containers
echo -e "${YELLOW}Running containers:${NC}"
docker-compose ps

# Clean up old images
echo -e "${YELLOW}Cleaning up old Docker images...${NC}"
docker image prune -f

# Keep only last 5 database backups
echo -e "${YELLOW}Cleaning up old backups...${NC}"
ls -t "$BACKUP_DIR"/postgres_backup_*.sql 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Services are available at:${NC}"
echo -e "  - API: http://54.248.140.63:8087"
echo -e "  - Frontend: http://54.248.140.63:3000"
echo -e "  - Database: postgresql://54.248.140.63:5433"

# Show logs
echo -e "${YELLOW}Recent logs:${NC}"
docker-compose logs --tail=20