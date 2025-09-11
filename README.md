# Media Transcode Service

A high-performance media transcoding service with WebP support, face detection capabilities, and cloud storage integration.

## Features

- **Multi-format Support**: Video, Image, GIF, and WebP transcoding
- **WebP Optimization**: 79% better compression than GIF
- **Face Detection**: Optional face detection and clustering
- **Cloud Storage**: S3-compatible storage integration
- **Background Processing**: Celery-based async task processing
- **GPU Acceleration**: Hardware-accelerated encoding support
- **Docker Ready**: Production-ready containerization

## Architecture

```
src/transcode_service/
├── api/              # REST API endpoints
├── services/         # Core business logic
├── workers/          # Background task workers
├── database/         # Database models & migrations
├── models/           # Pydantic data models
├── core/             # Core configuration & utilities
├── app.py           # FastAPI application
└── main.py          # CLI entry point
```

## Quick Start

### Installation

```bash
# Install the package
pip install -e .

# With optional dependencies
pip install -e ".[dev,face-detection]"
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### Run Services

```bash
# Start API server
transcode-api

# Start worker
transcode-worker

# Start face detection worker (optional)
transcode-face-worker
```

### Docker Deployment

```bash
# Copy deployment files
cd deployment/

# Start services
docker-compose up -d
```

## Development

### Project Structure

- `src/transcode_service/` - Main application package
- `config/` - Configuration templates
- `deployment/` - Docker and deployment files
- `scripts/` - Utility scripts
- `tests/` - Test files (excluded from package)

### Commands

```bash
# Development install
pip install -e ".[dev]"

# Code formatting
black src/

# Type checking
mypy src/

# Run tests
pytest tests/
```

## API Usage

### Upload & Transcode

```bash
# Upload media for transcoding
curl -X POST "http://localhost:8000/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://example.com/video.mp4",
    "config_id": "webp_basic"
  }'
```

### WebP Configuration

```json
{
  "output_type": "webp",
  "webp_config": {
    "fps": 15,
    "width": 640,
    "height": 480,
    "quality": 85,
    "animated": true,
    "lossless": false
  }
}
```

## License

MIT License