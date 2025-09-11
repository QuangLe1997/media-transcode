# Media Transcode Service API Documentation

## 📋 Overview

Media Transcode Service là một hệ thống microservice để transcode media files (video/image) với khả năng face detection tích hợp. Hệ thống sử dụng Google Cloud PubSub cho message queue và PostgreSQL cho data storage.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client/UI     │───▶│   FastAPI App    │───▶│   PostgreSQL    │
│                 │    │   (Port 8087)    │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Google PubSub   │
                       │   Message Bus    │
                       └──────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ Task         │ │ Transcode    │ │ Face Detect  │
        │ Listener     │ │ Worker       │ │ Worker       │
        └──────────────┘ └──────────────┘ └──────────────┘
                                │               │
                                ▼               ▼
                        ┌──────────────────────────────┐
                        │        S3 Storage            │
                        │    (Skylink/AWS S3)          │
                        └──────────────────────────────┘
```

## 🔧 Service Components

### 1. **FastAPI Application** (`transcode_service.app`)
- **Port**: 8087
- **Purpose**: REST API endpoints for client interaction
- **Responsibilities**:
  - Accept transcode requests (file upload hoặc URL)
  - Validate input và configuration
  - Create database records
  - Publish messages to PubSub
  - Provide task status và results

### 2. **Task Listener** (`transcode_service.workers.task_listener`)
- **Purpose**: Lắng nghe PubSub messages để tạo tasks
- **Responsibilities**:
  - Listen trên subscription: `skl-transcode-cms-tasks-sub`
  - Parse incoming task creation messages
  - Create database records for new tasks
  - Distribute work to appropriate workers
  - Handle task retry logic

### 3. **Transcode Worker** (`transcode_service.workers.transcode_worker`)
- **Purpose**: Xử lý video/image transcoding
- **Responsibilities**:
  - Listen trên subscription: `transcode-utils-tasks-sub`
  - Download media từ URL/S3
  - Execute FFmpeg operations
  - Upload outputs to S3
  - Update database với results

### 4. **Face Detection Worker** (`transcode_service.workers.face_detect_worker`)
- **Purpose**: AI-powered face detection và recognition
- **Responsibilities**:
  - Listen trên subscription: `face-detection-worker-tasks-sub`
  - Process images/videos for faces
  - Generate face avatars và metadata
  - Upload results to S3
  - Store face data in database

## 📚 API Endpoints

### Core Endpoints

#### `POST /transcode`
Tạo transcode task mới

**Request Body (multipart/form-data):**
```javascript
{
  // Input (chọn 1 trong 2)
  "video": File,                    // File upload
  "media_url": "string",           // Media URL

  // Required configs
  "profiles": "[{...}]",           // JSON array of transcode profiles
  "s3_output_config": "{...}",     // JSON object S3 config

  // Optional
  "face_detection_config": "{...}", // JSON object face detection config
  "callback_url": "string",         // Webhook URL
  "callback_auth": "{...}",         // Auth for callback
  "pubsub_topic": "string"          // PubSub notification topic
}
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "processing",
  "source_url": "string",
  "input_type": "file|url",
  "profiles_count": 3,
  "media_detection": {
    "detected_type": "video",
    "original_profiles": 5,
    "filtered_profiles": 3,
    "skipped_profiles": ["image-profile"]
  },
  "face_detection_enabled": true,
  "face_detection_published": true
}
```

#### `GET /task/{task_id}`
Lấy thông tin chi tiết task

**Response:**
```json
{
  "task_id": "uuid",
  "status": "completed|failed|processing|pending",
  "source_url": "string",
  "created_at": "ISO-datetime",
  "updated_at": "ISO-datetime",
  "outputs": {
    "profile-1": [
      {
        "url": "s3-url",
        "metadata": {
          "width": 1920,
          "height": 1080,
          "duration": 60.5,
          "codec": "h264"
        },
        "size": 1024000
      }
    ]
  },
  "failed_profiles": ["profile-name"],
  "profiles": [
    {
      "id": "profile-1",
      "display_name": "HD Video",
      "output_type": "video",
      "config_summary": "H264 | 1920x1080 | 30fps"
    }
  ],
  "expected_profiles": 3,
  "completed_profiles": 2,
  "failed_profiles_count": 1,
  "completion_percentage": 66.7,
  "face_detection_enabled": true,
  "face_detection_status": "completed",
  "face_detection_results": {
    "faces": [
      {
        "name": "face_0",
        "index": 0,
        "bounding_box": [x, y, w, h],
        "gender": "male",
        "age": 25,
        "group_size": 15,
        "avatar_url": "s3-url",
        "face_image_url": "s3-url"
      }
    ],
    "is_change_index": false
  }
}
```

#### `GET /tasks`
List tasks với pagination

**Query Parameters:**
- `status`: TaskStatus filter
- `limit`: Number of tasks (default: 50)
- `offset`: Pagination offset (default: 0)
- `include_details`: Include full task data (default: false)

#### `GET /tasks/summary`
Task statistics summary

**Response:**
```json
{
  "total_tasks": 150,
  "status_counts": {
    "completed": 120,
    "processing": 15,
    "failed": 10,
    "pending": 5
  },
  "statuses": {
    "pending": 5,
    "processing": 15,
    "completed": 120,
    "failed": 10
  }
}
```

#### `POST /task/{task_id}/retry`
Retry failed task

**Query Parameters:**
- `delete_files`: Delete existing S3 files (default: false)

#### `DELETE /task/{task_id}`
Delete task

**Query Parameters:**
- `delete_files`: Delete S3 files (default: false)
- `delete_faces`: Delete face detection files (default: false)

#### `POST /task/{task_id}/callback`
Resend callback for completed task

### Health Check Endpoints

#### `GET /health`
Simple health check
```json
{"status": "healthy"}
```

#### `GET /health/detailed`
Detailed health with timing
```json
{
  "status": "healthy",
  "timestamp": 1694123456.789,
  "server": "transcode-api",
  "version": "1.0.0"
}
```

#### `GET /health/db`
Health check with database test
```json
{
  "status": "healthy",
  "database": {
    "status": "connected",
    "query_result": 1,
    "connection_time_ms": 5.2
  },
  "response_time_ms": 10.5
}
```

### Config Template Management

#### `GET /config-templates`
List all configuration templates

#### `GET /config-templates/{template_id}`
Get specific template

#### `POST /config-templates`
Create new template

#### `PUT /config-templates/{template_id}`
Update existing template

#### `DELETE /config-templates/{template_id}`
Delete template

## 🔄 Workflow & Data Flow

### 1. **Task Creation Flow**

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB
    participant PubSub
    participant TaskListener
    
    Client->>API: POST /transcode
    API->>API: Validate input & detect media type
    API->>API: Filter profiles by media type
    API->>DB: Create task record
    API->>PubSub: Publish messages for each profile
    API->>Client: Return task_id & status
    
    PubSub->>TaskListener: Deliver task messages
    TaskListener->>DB: Update task status
    TaskListener->>PubSub: Distribute to workers
```

### 2. **Processing Flow**

```mermaid
sequenceDiagram
    participant PubSub
    participant TranscodeWorker
    participant FaceWorker
    participant FFmpeg
    participant S3
    participant DB
    
    PubSub->>TranscodeWorker: Transcode message
    TranscodeWorker->>TranscodeWorker: Download media
    TranscodeWorker->>FFmpeg: Execute transcode
    TranscodeWorker->>S3: Upload output
    TranscodeWorker->>DB: Update task result
    TranscodeWorker->>PubSub: Publish result
    
    PubSub->>FaceWorker: Face detection message
    FaceWorker->>FaceWorker: Download media
    FaceWorker->>FaceWorker: Run AI models
    FaceWorker->>S3: Upload face avatars
    FaceWorker->>DB: Update face results
```

### 3. **Result Aggregation Flow**

```mermaid
sequenceDiagram
    participant ResultSubscriber
    participant DB
    participant CallbackService
    participant Client
    
    ResultSubscriber->>DB: Listen for result updates
    ResultSubscriber->>DB: Check task completion
    
    alt All profiles completed
        ResultSubscriber->>DB: Update task status to COMPLETED
        ResultSubscriber->>CallbackService: Trigger callback
        CallbackService->>Client: Send webhook notification
    else Some profiles failed
        ResultSubscriber->>DB: Update task status to PARTIAL/FAILED
    end
```

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# API
API_HOST=0.0.0.0
API_PORT=8087
DEBUG=true

# Google Cloud PubSub
PUBSUB_PROJECT_ID=your-project-id
PUBSUB_TASKS_TOPIC=transcode-utils-tasks
TASKS_SUBSCRIPTION=transcode-utils-tasks-sub
PUBSUB_RESULTS_TOPIC=transcode-utils-results
PUBSUB_RESULTS_SUBSCRIPTION=transcode-utils-results-sub
PUBSUB_PUBLISHER_CREDENTIALS_PATH=/path/to/credentials.json
PUBSUB_SUBSCRIBER_CREDENTIALS_PATH=/path/to/credentials.json

# Face Detection PubSub
PUBSUB_FACE_DETECTION_TASKS_TOPIC=face-detection-worker-tasks
PUBSUB_FACE_DETECTION_RESULTS_TOPIC=face-detection-worker-results
FACE_DETECTION_SUBSCRIPTION=face-detection-worker-tasks-sub

# AWS S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_BUCKET_NAME=your-bucket
AWS_ENDPOINT_URL=https://storage.provider.com
AWS_ENDPOINT_PUBLIC_URL=https://public.cdn.com
AWS_BASE_FOLDER=transcode-service
```

### Profile Configuration Examples

#### Video Profile
```json
{
  "id_profile": "hd_h264",
  "output_type": "video",
  "input_types": ["video"],
  "video_config": {
    "codec": "h264",
    "max_width": 1920,
    "max_height": 1080,
    "bitrate": "2000k",
    "fps": 30,
    "preset": "medium",
    "crf": 23
  }
}
```

#### Image Profile
```json
{
  "id_profile": "thumbnail_jpg",
  "output_type": "image", 
  "input_types": ["image", "video"],
  "image_config": {
    "format": "jpg",
    "max_width": 300,
    "max_height": 200,
    "quality": 85
  }
}
```

#### GIF Profile
```json
{
  "id_profile": "preview_gif",
  "output_type": "gif",
  "input_types": ["video"],
  "gif_config": {
    "width": 480,
    "height": 270,
    "fps": 15,
    "duration": 5,
    "start_time": 0,
    "quality": 75
  }
}
```

#### Face Detection Config
```json
{
  "enabled": true,
  "similarity_threshold": 0.6,
  "min_faces_in_group": 3,
  "sample_interval": 5,
  "face_detector_score_threshold": 0.5,
  "avatar_size": 112,
  "avatar_quality": 85
}
```

## 📊 Monitoring & Debugging

### Logs Location
- API: `logs/api.log`
- Task Listener: `logs/task_listener.log`
- Transcode Worker: `logs/consumer.log`
- Face Detection Worker: `logs/face_detect_consumer.log`

### Key Metrics to Monitor
1. **Task Creation Rate**: POST /transcode requests/minute
2. **Processing Time**: Average time per task completion
3. **Success Rate**: Completed vs Failed tasks ratio
4. **Queue Depth**: PubSub message backlog
5. **Resource Usage**: CPU/Memory per worker
6. **S3 Upload Speed**: Network performance
7. **Database Connections**: Connection pool usage

### Common Issues & Troubleshooting

#### 1. Task Stuck in Processing
- Check worker health: `GET /health`
- Verify PubSub connectivity
- Check disk space for temp files
- Monitor FFmpeg processes

#### 2. High Failure Rate
- Validate input media URLs
- Check S3 credentials
- Monitor FFmpeg errors in logs
- Verify profile configurations

#### 3. Slow Processing
- Scale workers horizontally
- Optimize FFmpeg settings
- Check network bandwidth to S3
- Monitor database query performance

#### 4. Face Detection Issues
- Verify model files downloaded
- Check ONNX runtime installation
- Monitor GPU/CPU usage
- Validate input media format

## 🚀 Deployment & Scaling

### Horizontal Scaling
- Multiple worker instances can run in parallel
- Each worker type (transcode/face) can scale independently
- PubSub handles load balancing automatically

### Performance Tuning
- Adjust `WORKER_CONCURRENCY` environment variable
- Tune FFmpeg presets for speed vs quality
- Configure appropriate temp storage
- Optimize database connection pools

### Resource Requirements
- **API**: 512MB RAM, 1 CPU core
- **Transcode Worker**: 1-2GB RAM, 2-4 CPU cores
- **Face Detection Worker**: 2-4GB RAM, GPU recommended
- **Database**: PostgreSQL 15+, SSD storage recommended

---

*Generated by Media Transcode Service v1.0.0*