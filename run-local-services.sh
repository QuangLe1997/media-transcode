#!/bin/bash

# Script to run all local services with Docker database and Redis
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Local Transcode Services${NC}"
echo -e "${BLUE}=====================================${NC}"

# Load environment variables
if [ -f .env.local.services ]; then
    echo -e "${GREEN}📁 Loading environment from .env.local.services${NC}"
    export $(cat .env.local.services | xargs)
else
    echo -e "${RED}❌ .env.local.services file not found${NC}"
    exit 1
fi

# Function to start a service in background
start_service() {
    local service_name=$1
    local command=$2
    local log_file="logs/${service_name}.log"
    
    echo -e "${YELLOW}🔄 Starting ${service_name}...${NC}"
    mkdir -p logs
    
    # Kill existing process if running
    pkill -f "$command" 2>/dev/null || true
    
    # Start new process in background
    nohup bash -c "$command" > "$log_file" 2>&1 &
    local pid=$!
    
    echo -e "${GREEN}✅ Started ${service_name} (PID: ${pid})${NC}"
    echo -e "${GREEN}   Log: ${log_file}${NC}"
    
    # Give service time to start
    sleep 2
}

# Check Docker services
echo -e "${BLUE}🔍 Checking Docker services...${NC}"
if ! docker-compose -f docker-compose.services.yml ps | grep -q "healthy"; then
    echo -e "${YELLOW}⚠️  Docker services not healthy, starting them...${NC}"
    docker-compose -f docker-compose.services.yml up -d
    echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
    sleep 10
fi

# Start API service
start_service "api" "python -m transcode_service.api.main"

# Start Celery worker
start_service "worker" "celery -A transcode_service.workers.celery_config.celery_app worker --loglevel=info"

echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}📍 API: http://localhost:8087${NC}"
echo -e "${GREEN}📍 API Docs: http://localhost:8087/docs${NC}"
echo -e "${GREEN}📍 Health Check: http://localhost:8087/health${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "${YELLOW}📋 To stop services: pkill -f 'transcode'${NC}"
echo -e "${YELLOW}📋 To view logs: tail -f logs/api.log logs/worker.log${NC}"