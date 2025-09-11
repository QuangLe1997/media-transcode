#!/bin/bash

# Docker management script for local development

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.local.yml"

usage() {
    echo "Usage: $0 {build|up|down|logs|status|clean|restart|shell}"
    echo ""
    echo "Commands:"
    echo "  build    - Build Docker images"
    echo "  up       - Start services in background"
    echo "  down     - Stop and remove services"
    echo "  logs     - Show logs from all services"
    echo "  status   - Show service status"
    echo "  clean    - Remove containers, volumes and images"
    echo "  restart  - Restart all services"
    echo "  shell    - Open shell in API container"
    echo ""
    echo "Examples:"
    echo "  $0 build         # Build images"
    echo "  $0 up            # Start services"
    echo "  $0 logs api      # Show API logs only"
    echo "  $0 logs -f       # Follow all logs"
}

build() {
    echo "🔨 Building Docker images for local development..."
    docker-compose -f "$COMPOSE_FILE" build "$@"
}

up() {
    echo "🚀 Starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d "$@"
    echo ""
    echo "✅ Services started! Check status with: $0 status"
    echo "🌐 API available at: http://localhost:8087"
    echo "📊 PostgreSQL available at: localhost:5433"
    echo "📊 Redis available at: localhost:6379"
}

down() {
    echo "🛑 Stopping services..."
    docker-compose -f "$COMPOSE_FILE" down "$@"
}

logs() {
    docker-compose -f "$COMPOSE_FILE" logs "$@"
}

status() {
    echo "📊 Service Status:"
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    
    echo "🔍 Health Checks:"
    # Check API health
    if curl -s -f http://localhost:8087/health > /dev/null 2>&1; then
        echo "✅ API (localhost:8087) - Healthy"
    else
        echo "❌ API (localhost:8087) - Not responding"
    fi
    
    # Check PostgreSQL
    if docker exec transcode-postgres-local pg_isready -U transcode_user -d transcode_db > /dev/null 2>&1; then
        echo "✅ PostgreSQL (localhost:5433) - Ready"
    else
        echo "❌ PostgreSQL (localhost:5433) - Not ready"
    fi
    
    # Check Redis
    if docker exec transcode-redis-local redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis (localhost:6379) - Connected"
    else
        echo "❌ Redis (localhost:6379) - Not connected"  
    fi
}

clean() {
    echo "🧹 Cleaning up Docker resources..."
    read -p "This will remove all containers, volumes and images. Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
        docker-compose -f "$COMPOSE_FILE" rm -f
        docker system prune -f
        echo "✅ Cleanup completed"
    else
        echo "❌ Cleanup cancelled"
    fi
}

restart() {
    echo "🔄 Restarting services..."
    down
    sleep 2
    up
}

shell() {
    echo "🐚 Opening shell in API container..."
    docker exec -it transcode-api-local /bin/bash
}

# Main script
cd "$SCRIPT_DIR"

case "$1" in
    build)
        shift
        build "$@"
        ;;
    up)
        shift
        up "$@"
        ;;
    down)
        shift
        down "$@"
        ;;
    logs)
        shift
        logs "$@"
        ;;
    status)
        status
        ;;
    clean)
        clean
        ;;
    restart)
        restart
        ;;
    shell)
        shell
        ;;
    *)
        usage
        exit 1
        ;;
esac