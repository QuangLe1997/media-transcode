# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Commands
```bash
# Start development environment
python app.py                    # Run Flask app directly (development)
celery -A tasks.celery_config.celery_app worker -l info  # Start Celery worker
redis-server                     # Start Redis server

# Initialize database
python init_db.py                # Initialize database tables

# Testing
python -m pytest tests/         # Run tests
python -m pytest --cov=. tests/ # Run tests with coverage
```

### Docker Commands
```bash
# Quick development setup
./deploy.sh init                 # Initialize environment and directories
./deploy.sh start               # Start all services with docker-compose
./deploy.sh stop                # Stop all services
./deploy.sh logs                # View logs from all services
./deploy.sh build               # Build Docker images

# Production deployment
./deploy.sh -e production init   # Initialize production environment
./deploy.sh -e production start # Start production services
./deploy.sh -e production logs  # View production logs

# Service-specific commands
./deploy.sh -s web logs         # View logs for specific service
./deploy.sh -s worker restart   # Restart specific service
```

### Code Quality Commands
```bash
# Linting and formatting
black .                         # Format Python code
flake8 .                       # Check code style
```

### Server Deployment Commands
```bash
# Server connection
ssh skl@192.168.0.234:6789     # Connect to deployment server

# Sync local changes to server (excludes unnecessary files)
rsync -av --exclude='*.pyc' --exclude='__pycache__' --exclude='.git' --exclude='instance/' --exclude='uploads/' --exclude='.env' --exclude='.DS_Store' --exclude='*.log' ./ skl@192.168.0.234:6789:/quang/quang/transcode/

# Server deployment workflow (run on server)
cd /quang/quang/transcode
./deploy.sh -e production build  # Build Docker images
./deploy.sh -e production start  # Start services
./deploy.sh -e production logs   # Check logs for issues
```

## Architecture

### High-Level Architecture
This is a Docker-based media transcoding system with a Flask web application, Celery workers for background processing, and Redis for task queuing. The system processes video and image files through configurable transcoding profiles.

**Core Components:**
- **Flask Web App**: RESTful API and web interface for job management
- **Celery Workers**: Background processing of media transcoding tasks
- **Redis**: Message broker for Celery task queue
- **SQLite/PostgreSQL**: Database for storing jobs, configs, and metadata
- **FFmpeg**: Core media processing engine with GPU acceleration support
- **S3/MinIO**: Optional cloud storage for input/output files

### Directory Structure
```
├── api/                    # REST API endpoints (auth, jobs, configs, media)
├── database/              # Database models and migrations
├── services/              # Core business logic services
│   ├── ffmpeg_service.py  # FFmpeg integration and media processing
│   ├── transcode_service.py # High-level transcoding orchestration
│   ├── face_detect_service.py # Face detection and analysis
│   └── s3_service.py      # S3/cloud storage integration
├── tasks/                 # Celery background tasks
│   ├── video_tasks.py     # Video processing tasks
│   └── image_tasks.py     # Image processing tasks
├── templates/             # Jinja2 HTML templates
├── static/               # Frontend assets (CSS, JS)
├── uploads/              # Local file storage
├── config_samples/       # Configuration profile templates
└── monitoring/           # Prometheus/Grafana monitoring configs
```

### Database Schema
Key relationships:
- `User` → `Config` (1:N) - Users create transcoding configurations
- `User` → `Job` (1:N) - Users submit transcoding jobs  
- `Job` → `Media` (1:N) - Jobs contain multiple media files
- `Media` → `TranscodeTask` (1:N) - Each media file generates multiple tasks
- `TranscodeTask` → `TranscodeOutput` (1:N) - Tasks produce multiple output files

### Configuration System
Uses JSON-based configuration profiles stored in `Config` model. Configurations define:
- **Video transcoding profiles**: Resolution, codec, quality, GPU acceleration
- **Image processing profiles**: Format conversion, compression, resizing
- **Face detection settings**: Detection thresholds, clustering parameters
- **Output settings**: Storage paths, file naming, S3 integration

See `CONFIG_PROFILES_DOCUMENTATION.md` for detailed configuration schema.

### Task Processing Flow
1. User uploads media files and selects config profile
2. `TranscodeService` creates `Media` records and `TranscodeTask` entries
3. Celery workers pull tasks from Redis queue
4. `FFmpegService` processes media using profile parameters
5. Outputs stored locally and/or uploaded to S3
6. `TranscodeOutput` records track generated files

### GPU Acceleration
System auto-detects available hardware encoders:
- **NVIDIA**: `h264_nvenc`, `hevc_nvenc` 
- **AMD**: `h264_amf`
- **Intel**: `h264_qsv`
- **Apple Silicon**: `h264_videotoolbox`
- **Fallback**: Software encoding with `libx264`

Hardware acceleration configured in Docker Compose with GPU device reservations.

## Development Practices

### Development Workflow
**Local Development → Server Deployment Cycle:**
1. **Local Development**: Make code changes and test locally
2. **Code Sync**: Use rsync to sync only necessary files to server (excludes cache, logs, etc.)
3. **Server Build**: SSH to server and rebuild Docker images
4. **Deploy & Test**: Start services and check logs for issues
5. **Debug**: If issues found, fix locally and repeat cycle

**Server Information:**
- SSH: `skl@192.168.0.234:6789`
- Project Path: `/quang/quang/transcode`
- Environment: Production with PostgreSQL and Redis

### Environment Setup
- Copy `.env.example` to `.env` and configure environment variables
- Use `./deploy.sh init` to create required directories
- Development uses SQLite, production uses PostgreSQL
- Redis required for Celery task queue

### Configuration Management
- Config profiles stored as JSON in database
- Default templates in `config_samples/` directory
- Use `static/js/config-builder.js` for UI-based config creation
- Validate JSON configs before saving

### Error Handling
- Tasks track status: `pending` → `processing` → `completed/failed`
- Detailed error messages stored in `TranscodeTask.error_message`
- Failed tasks can be retried through Celery
- Progress reporting via Celery task updates

### Face Detection (Optional)
- Uses ONNX models for face detection and recognition
- Models stored in `models/` and `services/models/` directories
- Fallback to mock processor if models unavailable
- Configurable detection thresholds and clustering parameters

### Storage Integration
- Local storage in `uploads/` directory for development
- S3-compatible storage (AWS S3, MinIO) for production
- Configurable file naming and folder structures
- Automatic cleanup options for temporary files

## Important Notes

- The system uses singleton pattern for `FFmpegService` to manage resource usage
- GPU acceleration requires proper Docker GPU runtime setup
- Face detection models are optional - system gracefully degrades without them
- Configuration profiles are versioned and can be shared between users
- All media processing is asynchronous via Celery task queue
- Use `flower` service to monitor Celery task status and performance