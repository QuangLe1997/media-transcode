#!/bin/bash

# Build and run local Docker Compose setup (no GPU)
# Usage: ./build-local.sh [build|up|down|logs|clean]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

COMPOSE_FILE="deployment/docker-compose.local.yml"
PROJECT_NAME="transcode-local"

echo -e "${BLUE}🐳 Media Transcode Local Docker Setup${NC}"
echo "================================================"

# Function to display usage
usage() {
    echo "Usage: $0 [build|up|down|logs|clean|ps|restart]"
    echo ""
    echo "Commands:"
    echo "  build    - Build all Docker images"
    echo "  up       - Start all services in background"
    echo "  down     - Stop and remove all containers"
    echo "  logs     - Show logs from all services"
    echo "  clean    - Remove all containers, images, and volumes"
    echo "  ps       - Show running containers"
    echo "  restart  - Restart all services"
    echo ""
    exit 1
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
        exit 1
    fi
}

# Build images
build_images() {
    echo -e "${YELLOW}🔨 Building Docker images...${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME build --no-cache
    echo -e "${GREEN}✅ Build completed successfully!${NC}"
}

# Start services
start_services() {
    echo -e "${YELLOW}🚀 Starting services...${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d
    
    echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
    sleep 10
    
    # Check API health
    echo -e "${YELLOW}🔍 Checking API health...${NC}"
    for i in {1..30}; do
        if curl -f http://localhost:8087/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API is healthy!${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}❌ API health check timeout${NC}"
            echo "Try: docker-compose -f $COMPOSE_FILE logs api"
        else
            echo -n "."
            sleep 2
        fi
    done
    
    echo ""
    echo -e "${GREEN}🎉 All services started successfully!${NC}"
    echo ""
    echo "Services running:"
    echo "  📡 API Server: http://localhost:8087"
    echo "  📖 API Docs: http://localhost:8087/docs"
    echo "  🗄️  Database: localhost:5433"
    echo ""
    echo "Useful commands:"
    echo "  View logs: ./build-local.sh logs"
    echo "  Stop services: ./build-local.sh down"
    echo "  Check status: ./build-local.sh ps"
}

# Stop services
stop_services() {
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down
    echo -e "${GREEN}✅ Services stopped${NC}"
}

# Show logs
show_logs() {
    echo -e "${YELLOW}📋 Showing logs (press Ctrl+C to exit)...${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f
}

# Clean everything
clean_all() {
    echo -e "${YELLOW}🧹 Cleaning up everything...${NC}"
    
    # Stop and remove containers
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v --remove-orphans
    
    # Remove images
    echo -e "${YELLOW}Removing images...${NC}"
    docker images --format "table {{.Repository}}:{{.Tag}}\t{{.ID}}" | grep "$PROJECT_NAME" | awk '{print $2}' | xargs -r docker rmi -f
    
    # Remove volumes
    echo -e "${YELLOW}Removing volumes...${NC}"
    docker volume ls --format "table {{.Name}}" | grep "$PROJECT_NAME" | xargs -r docker volume rm
    
    # Remove networks
    echo -e "${YELLOW}Removing networks...${NC}"
    docker network ls --format "table {{.Name}}" | grep "$PROJECT_NAME" | xargs -r docker network rm
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Show container status
show_status() {
    echo -e "${YELLOW}📊 Container status:${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
}

# Restart services
restart_services() {
    echo -e "${YELLOW}🔄 Restarting services...${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME restart
    echo -e "${GREEN}✅ Services restarted${NC}"
}

# Main script
main() {
    check_docker
    
    case "${1:-help}" in
        "build")
            build_images
            ;;
        "up")
            start_services
            ;;
        "down")
            stop_services
            ;;
        "logs")
            show_logs
            ;;
        "clean")
            clean_all
            ;;
        "ps")
            show_status
            ;;
        "restart")
            restart_services
            ;;
        "help"|*)
            usage
            ;;
    esac
}

main "$@"