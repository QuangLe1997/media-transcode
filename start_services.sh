#!/bin/bash

# Start all transcode services
# Usage: ./start_services.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Media Transcode Services...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r deployment/requirements-base.txt
else
    source .venv/bin/activate
fi

# Create necessary directories
mkdir -p logs
mkdir -p /tmp/transcode

# Function to start a service in background
start_service() {
    local name=$1
    local command=$2
    local log_file="logs/${name}.log"
    
    echo -e "${YELLOW}Starting ${name}...${NC}"
    nohup $command > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "logs/${name}.pid"
    echo -e "${GREEN}✓ ${name} started (PID: $pid)${NC}"
}

# Start API server
start_service "api" "python -m transcode_service.app"

# Wait for API to be ready
echo -e "${YELLOW}Waiting for API to be ready...${NC}"
sleep 5

# Check API health
if curl -f http://localhost:8086/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${YELLOW}⚠ API health check failed, but continuing...${NC}"
fi

# Start task listener (PubSub listener for incoming tasks)
start_service "task-listener" "python -m transcode_service.workers.task_listener"

# Start transcode worker (processes transcode tasks)
start_service "transcode-worker" "python -m transcode_service.workers.transcode_worker"

# Start face detection worker
start_service "face-detect-worker" "python -m transcode_service.workers.face_detect_worker"

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""
echo "Services running:"
echo "  - API Server: http://localhost:8086"
echo "  - Task Listener: Processing incoming task messages"
echo "  - Transcode Worker: Processing transcode tasks"
echo "  - Face Detection Worker: Processing face detection tasks"
echo ""
echo "Logs are available in: ./logs/"
echo ""
echo "To stop all services, run: ./stop_services.sh"
echo ""
echo -e "${YELLOW}Monitoring logs...${NC}"
echo "Press Ctrl+C to exit (services will continue running in background)"
echo ""

# Show combined logs
tail -f logs/*.log