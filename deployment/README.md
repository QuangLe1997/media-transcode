# Docker Deployment Guide

This project supports two deployment configurations:

## 1. Local Development (No GPU/CUDA)

For local development on machines without GPU support:

### Build & Run
```bash
cd deployment/

# Build images
docker-compose -f docker-compose.local.yml build

# Start services
docker-compose -f docker-compose.local.yml up -d

# View logs
docker-compose -f docker-compose.local.yml logs -f

# Stop services
docker-compose -f docker-compose.local.yml down
```

### Features
- Uses `python:3.11-slim` base image
- CPU-only FFmpeg processing
- CPU-only OpenCV and ONNX Runtime
- Simplified services (API + Worker + PostgreSQL + Redis)
- No GPU acceleration requirements
- Faster builds and smaller images

## 2. Server Production (With GPU/CUDA)

For production deployment on GPU-enabled servers:

### Build & Run
```bash
cd deployment/

# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Features
- Uses `nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04` base image
- GPU-accelerated FFmpeg processing
- GPU-accelerated ONNX Runtime and CUDA libraries
- Full services including face detection worker
- CUDA/GPU hardware acceleration
- Requires NVIDIA Docker runtime

## Configuration

### Environment Variables
Copy and configure environment file:
```bash
cp .env.example .env
# Edit .env with your settings
```

### Port Configuration
- **Local**: API runs on `localhost:8087`
- **Production**: API runs on `localhost:8087`
- **PostgreSQL**: Available on `localhost:5433`
- **Redis** (local only): Available on `localhost:6379`

## Services

### Local Development Services
- `postgres` - PostgreSQL database
- `redis` - Redis for task queue
- `api` - Flask web API
- `worker` - Background transcode worker

### Production Services
- `postgres` - PostgreSQL database
- `api` - Flask web API
- `consumer` - Background transcode worker
- `face-detection-worker` - Face detection processing
- `task-listener` - PubSub task listener
- `frontend` - React frontend

## Health Checks

All services include health checks:
```bash
# Check service health
docker-compose ps

# Check API health directly
curl http://localhost:8087/health
```

## Troubleshooting

### Common Issues

1. **GPU not available**: Use local configuration
2. **Port conflicts**: Change ports in docker-compose files
3. **Out of memory**: Adjust memory limits in compose files
4. **Build failures**: Ensure Docker daemon is running

### Logs
```bash
# View specific service logs
docker-compose logs -f api
docker-compose logs -f worker

# View all logs
docker-compose logs -f
```

## File Structure

```
deployment/
├── Dockerfile.cuda          # CUDA/GPU version
├── Dockerfile.local         # Local development version
├── docker-compose.yml       # Production with GPU
├── docker-compose.local.yml # Local development
├── requirements.txt         # Python dependencies
├── requirements-face-detection.txt # Face detection dependencies
└── .env                     # Environment variables
```