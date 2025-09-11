# Transcode Service API

Modern media transcoding service with FastAPI, React frontend, and PostgreSQL.

## ✨ Features

- **Unified API** - Single `/transcode` endpoint for file upload and URL input
- **React Frontend** - Modern UI with Monaco JSON editor
- **JSON Configuration** - Flexible profile and S3 output settings
- **PostgreSQL Database** - Reliable task tracking and results
- **Docker Deployment** - Easy containerized deployment
- **Health Monitoring** - Built-in health checks and logging

## 🚀 Quick Deploy

### Option 1: Docker (Recommended)

```bash
# 1. Clone and setup
git clone <repo-url>
cd magic-transcode-media

# 2. Configure environment
cp .env.template .env
nano .env  # Update with your settings

# 3. Deploy with one command
./deploy.sh
```

### Option 2: Manual Docker

```bash
# Start all services
docker-compose up --build -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## 🔧 Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# AWS S3 Storage
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_BUCKET_NAME=your_bucket
AWS_ENDPOINT_URL=https://storage.provider.com
AWS_ENDPOINT_PUBLIC_URL=https://static.provider.com
AWS_BASE_FOLDER=transcode-service

# Google Cloud Pub/Sub (optional)
PUBSUB_PROJECT_ID=your_project_id
PUBSUB_TASKS_TOPIC=transcode-tasks
PUBSUB_RESULTS_TOPIC=transcode-results
# Add key.json file for Pub/Sub credentials
```

## 📡 API Usage

### Single Unified Endpoint: `POST /transcode`

**File Upload:**
```bash
curl -X POST "http://localhost:8087/transcode" \
  -F "video=@video.mp4" \
  -F 'profiles=[{"id_profile":"720p","output_type":"video","video_config":{"codec":"libx264","max_width":1280,"max_height":720,"bitrate":"2M"}}]' \
  -F 's3_output_config={"base_path":"outputs","folder_structure":"{task_id}/{profile_id}"}'
```

**URL Input:**
```bash
curl -X POST "http://localhost:8087/transcode" \
  -F "media_url=https://example.com/video.mp4" \
  -F 'profiles=[{"id_profile":"720p","output_type":"video","video_config":{"codec":"libx264","max_width":1280,"max_height":720,"bitrate":"2M"}}]' \
  -F 's3_output_config={"base_path":"outputs","folder_structure":"{task_id}/{profile_id}"}'
```

### Other Endpoints

- `GET /health` - Health check
- `GET /tasks` - List all tasks
- `GET /task/{id}` - Get task details
- `DELETE /task/{id}` - Delete task
- `GET /docs` - API documentation

## 🖥️ Frontend Usage

Access the React frontend at `http://localhost:3000`

### Features:
- **Drag & Drop** file upload
- **URL input** for remote media
- **Monaco Editor** for JSON configuration with:
  - Syntax highlighting
  - Auto-formatting
  - Quick templates (720p, 1080p, thumbnails, GIF)
  - Error detection
- **Real-time** task monitoring
- **Responsive** design

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React         │    │   FastAPI       │    │   PostgreSQL    │
│   Frontend      │───▶│   Backend       │───▶│   Database      │
│   (Port 3000)   │    │   (Port 8087)   │    │   (Port 5433)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                       ┌───────┴────────┐
                       │   Consumer      │
                       │   Worker        │
                       └────────────────┘
```

## 🔧 Development

### Local Development

```bash
# Backend
python main.py

# Frontend
cd frontend
npm start

# Database
docker run -d -p 5433:5432 postgres:15-alpine
```

### Project Structure

```
├── main.py                    # Server entry point
├── api/main.py               # FastAPI routes
├── db/                       # Database models & operations
├── consumer/                 # Background worker
├── services/                 # S3, Pub/Sub services
├── frontend/                 # React application
│   ├── src/components/       # React components  
│   ├── Dockerfile           # Frontend container
│   └── nginx.conf           # Nginx configuration
├── docker-compose.yml       # All services
├── Dockerfile              # Backend container
└── deploy.sh              # Deployment script
```

## 📊 Monitoring

### Service URLs (after deployment)
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8087
- **API Docs**: http://localhost:8087/docs
- **Database**: localhost:5433

### Useful Commands

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f frontend
docker-compose logs -f consumer

# Check service status
docker-compose ps

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart api
```

## 🔒 Security Features

- **Non-root containers** - All containers run as non-root users
- **Health checks** - Built-in health monitoring
- **Resource limits** - Memory and CPU constraints
- **CORS handling** - Proper cross-origin configuration
- **Input validation** - JSON schema validation
- **Error handling** - Comprehensive error responses

## 🚀 Production Deployment

The system is production-ready with:
- **Multi-stage Docker builds** for optimization
- **Health checks** for all services
- **Proper logging** with rotation
- **Resource management** and restart policies
- **Environment-based configuration**

For production deployment, update the IP addresses in:
- `frontend/.env.production`
- `docker-compose.yml` (if needed)

## 📝 JSON Configuration Examples

### Video Profile
```json
{
  "id_profile": "1080p_h264",
  "output_type": "video",
  "video_config": {
    "codec": "libx264",
    "max_width": 1920,
    "max_height": 1080,
    "bitrate": "4M",
    "preset": "medium"
  }
}
```

### Image Profile  
```json
{
  "id_profile": "thumbnail",
  "output_type": "image",
  "image_config": {
    "max_width": 400,
    "max_height": 300,
    "quality": 80,
    "format": "jpeg"
  }
}
```

### GIF Profile
```json
{
  "id_profile": "preview_gif", 
  "output_type": "gif",
  "gif_config": {
    "fps": 10,
    "width": 640,
    "duration": 5,
    "quality": 80
  }
}
```