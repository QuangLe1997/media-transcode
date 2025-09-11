#!/bin/bash

# Stop all transcode services
# Usage: ./stop_services.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Media Transcode Services...${NC}"

# Function to stop a service
stop_service() {
    local name=$1
    local pid_file="logs/${name}.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo -e "${YELLOW}Stopping ${name} (PID: $pid)...${NC}"
            kill $pid
            rm "$pid_file"
            echo -e "${GREEN}✓ ${name} stopped${NC}"
        else
            echo -e "${YELLOW}${name} not running (stale PID file)${NC}"
            rm "$pid_file"
        fi
    else
        echo -e "${YELLOW}${name} not running (no PID file)${NC}"
    fi
}

# Stop all services
stop_service "api"
stop_service "task-listener"
stop_service "transcode-worker"
stop_service "face-detect-worker"

# Also try to kill any remaining Python processes related to transcode_service
echo -e "${YELLOW}Cleaning up any remaining processes...${NC}"
pkill -f "transcode_service" 2>/dev/null || true

echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}All services stopped!${NC}"
echo -e "${GREEN}===========================================${NC}"