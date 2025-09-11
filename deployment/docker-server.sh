#!/bin/bash

# Docker management script for server deployment (with GPU/CUDA)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.yml"

usage() {
    echo "Usage: $0 {build|up|down|logs|status|clean|restart|gpu-test}"
    echo ""
    echo "Commands:"
    echo "  build     - Build Docker images with CUDA support"
    echo "  up        - Start services in background"
    echo "  down      - Stop and remove services"
    echo "  logs      - Show logs from all services"
    echo "  status    - Show service status"
    echo "  clean     - Remove containers, volumes and images"
    echo "  restart   - Restart all services"
    echo "  gpu-test  - Test GPU availability in containers"
    echo ""
    echo "Examples:"
    echo "  $0 build            # Build images with CUDA"
    echo "  $0 up               # Start all services"
    echo "  $0 logs consumer    # Show consumer logs"
    echo "  $0 gpu-test         # Check GPU in containers"
}

build() {
    echo "🔨 Building Docker images for server deployment (CUDA)..."
    echo "⚠️  This requires NVIDIA Docker runtime and CUDA base images"
    docker-compose -f "$COMPOSE_FILE" build "$@"
}

up() {
    echo "🚀 Starting services with GPU support..."
    docker-compose -f "$COMPOSE_FILE" up -d "$@"
    echo ""
    echo "✅ Services started! Check status with: $0 status"
    echo "🌐 API available at: http://localhost:8087"
    echo "📊 PostgreSQL available at: localhost:5433"
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
    if docker exec transcode-postgres pg_isready -U transcode_user -d transcode_db > /dev/null 2>&1; then
        echo "✅ PostgreSQL (localhost:5433) - Ready"
    else
        echo "❌ PostgreSQL (localhost:5433) - Not ready"
    fi
}

gpu_test() {
    echo "🔍 Testing GPU availability in containers..."
    echo ""
    
    # Test nvidia-smi in consumer
    echo "Testing Consumer container:"
    if docker exec transcode-consumer nvidia-smi > /dev/null 2>&1; then
        echo "✅ Consumer - GPU available"
        docker exec transcode-consumer nvidia-smi --query-gpu=name --format=csv,noheader
    else
        echo "❌ Consumer - No GPU access"
    fi
    
    echo ""
    echo "Testing Face Detection Worker:"
    if docker exec transcode-face-detection-worker nvidia-smi > /dev/null 2>&1; then
        echo "✅ Face Detection Worker - GPU available"
        docker exec transcode-face-detection-worker nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader
    else
        echo "❌ Face Detection Worker - No GPU access"
    fi
    
    echo ""
    echo "FFmpeg GPU encoders:"
    docker exec transcode-consumer ffmpeg -encoders | grep -i nvenc || echo "❌ No NVIDIA encoders found"
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
    gpu-test)
        gpu_test
        ;;
    *)
        usage
        exit 1
        ;;
esac