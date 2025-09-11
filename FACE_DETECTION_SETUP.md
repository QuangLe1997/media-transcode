# Face Detection Setup Guide

## Overview

The Transcode Service now supports face detection as part of the transcode workflow. Face detection runs in parallel with video/image transcoding and can detect, cluster, and extract face avatars from media files.

## Features

- ✅ **Face Detection**: Detect faces in videos and images
- ✅ **Face Clustering**: Group similar faces together using similarity thresholds
- ✅ **Face Recognition**: Extract face embeddings for matching
- ✅ **Avatar Generation**: Create face avatars with configurable quality
- ✅ **Parallel Processing**: Face detection runs alongside transcoding
- ✅ **S3 Integration**: Upload face avatars to S3 storage
- ✅ **Callback Integration**: Results included in task completion callbacks

## Requirements

### 1. Face Detection Models

Download the required ONNX models and place them in the `models_faces/` directory:

```
models_faces/
├── yoloface.onnx                 # Face detection model
├── arcface_w600k_r50.onnx        # Face recognition model
├── face_landmarker_68.onnx       # 68-point facial landmarks
├── face_landmarker_68_5.onnx     # 68-point to 5-point conversion
└── gender_age.onnx               # Gender and age prediction
```

### 2. Python Dependencies

Face detection requires additional Python packages (automatically installed with Docker):

```
opencv-python==4.8.1.78
scikit-learn==1.3.2
onnxruntime==1.16.3
tqdm==4.66.1
requests==2.31.0
```

## Deployment Options

### Option 1: Docker Compose with Face Detection (Recommended)

Use the dedicated face detection deployment script:

```bash
./deploy-with-face-detection.sh
```

This script will:
- ✅ Check for required face detection models
- ✅ Deploy all services including face detection worker
- ✅ Verify worker deployment
- ✅ Provide monitoring commands

### Option 2: Add Face Detection to Existing Deployment

Add face detection worker to existing deployment:

```bash
# Stop current services
docker-compose down

# Start with face detection
docker-compose -f docker-compose.yml -f docker-compose.face-detection.yml up -d
```

### Option 3: Integrated Docker Compose (Already Modified)

The main `docker-compose.yml` now includes face detection worker by default. Use regular deployment:

```bash
./deploy.sh
```

## Configuration

### Environment Variables

Add to your `.env` file (optional - defaults provided):

```bash
# Face Detection Pub/Sub Topics
PUBSUB_FACE_DETECTION_TASKS_TOPIC=face-detection-worker-tasks
PUBSUB_FACE_DETECTION_RESULTS_TOPIC=face-detection-worker-results

# Face Detection Worker
FACE_DETECTION_SUBSCRIPTION=face-detection-worker-tasks-sub

# Default Configuration (can be overridden per-task)
FACE_DETECTION_SIMILARITY_THRESHOLD=0.6
FACE_DETECTION_MIN_FACES_IN_GROUP=3
FACE_DETECTION_SAMPLE_INTERVAL=5
FACE_DETECTION_DETECTOR_SCORE_THRESHOLD=0.5
FACE_DETECTION_LANDMARKER_SCORE_THRESHOLD=0.85
FACE_DETECTION_AVATAR_SIZE=112
FACE_DETECTION_AVATAR_QUALITY=85
FACE_DETECTION_MAX_WORKERS=4
```

## API Usage

### Basic Face Detection Request

```bash
curl -X POST "http://localhost:8087/transcode" \\
  -F "media_url=https://example.com/video.mp4" \\
  -F 'profiles=[{"id_profile":"video_480p","output_type":"video","video_config":{"codec":"libx264","max_width":854,"max_height":480}}]' \\
  -F 's3_output_config={"bucket":"my-bucket","base_path":"outputs","folder_structure":"{task_id}/{profile_id}"}' \\
  -F 'face_detection_config={"enabled":true,"similarity_threshold":0.6,"min_faces_in_group":3,"save_faces":true}'
```

### Face Detection Configuration Options

```json
{
  "enabled": true,
  "similarity_threshold": 0.6,
  "min_faces_in_group": 3,
  "sample_interval": 5,
  "ignore_frames": [],
  "ignore_ranges": [],
  "start_frame": 0,
  "end_frame": null,
  "face_detector_size": "640x640",
  "face_detector_score_threshold": 0.5,
  "face_landmarker_score_threshold": 0.85,
  "iou_threshold": 0.4,
  "min_appearance_ratio": 0.25,
  "min_frontality": 0.2,
  "avatar_size": 112,
  "avatar_padding": 0.07,
  "avatar_quality": 85,
  "save_faces": true,
  "max_workers": 4
}
```

### API Response

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "face_detection_enabled": true,
  "face_detection_published": true,
  "profiles_count": 1
}
```

### Task Status with Face Detection

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "face_detection_enabled": true,
  "face_detection_status": "completed",
  "face_detection_results": {
    "faces": [
      {
        "name": "000001_00",
        "group_size": 5,
        "avatar": "base64_encoded_image",
        "bounding_box": [x1, y1, x2, y2],
        "detector": 0.95,
        "landmarker": 0.88,
        "gender": 1,
        "age": 25
      }
    ],
    "is_change_index": false,
    "output_urls": [
      "https://s3.example.com/bucket/task_id/faces/avatar_001.jpg"
    ],
    "completed_at": "2024-01-01T12:00:00Z"
  },
  "outputs": {
    "video_480p": [
      {
        "url": "https://s3.example.com/bucket/task_id/video_480p/output.mp4",
        "metadata": {...}
      }
    ]
  }
}
```

## Monitoring

### Check Worker Status

```bash
# Check all workers
docker ps --filter "name=transcode"

# Check face detection worker specifically
docker ps --filter "name=transcode-face-detection-worker"

# View face detection worker logs
docker logs transcode-face-detection-worker -f
```

### Monitor Processing

```bash
# Check API logs for face detection task publishing
docker logs transcode-api -f | grep "face detection"

# Check worker logs for face detection processing
docker logs transcode-face-detection-worker -f
```

## Task Completion Logic

A task is marked as `completed` when:

1. **All transcode profiles are completed** AND
2. **Face detection is completed** (if enabled)

If face detection fails but transcoding succeeds, the task will be marked as `completed` with a partial failure message.

## Troubleshooting

### Common Issues

1. **Missing Models**
   ```
   ❌ models_faces directory not found!
   ```
   **Solution**: Download required ONNX models to `models_faces/` directory

2. **Face Detection Worker Not Starting**
   ```bash
   docker logs transcode-face-detection-worker
   ```
   **Common causes**: Missing models, insufficient memory, dependency issues

3. **No Face Detection Results**
   - Check if `face_detection_config.enabled = true`
   - Verify face detector score thresholds
   - Check video/image quality and face visibility

4. **Performance Issues**
   - Reduce `sample_interval` for faster processing (less accuracy)
   - Adjust `max_workers` based on available CPU cores
   - Use smaller `face_detector_size` for faster detection

### Debugging Commands

```bash
# Test face detection models loading
docker exec transcode-face-detection-worker python -c "from services.face_detect_service import get_face_analyser; print('Models loaded successfully')"

# Check models directory mounting
docker exec transcode-face-detection-worker ls -la /app/models_faces/

# Test face detection API
python test_face_detection_api.py
```

## Performance Notes

- **CPU Usage**: Face detection is CPU-intensive; adjust `max_workers` accordingly
- **Memory Usage**: Each worker uses ~1-2GB RAM depending on model size
- **Processing Time**: Varies by video length, resolution, and number of faces
- **Storage**: Face avatars are typically 5-20KB each

## Model Information

| Model | Purpose | Size | Performance |
|-------|---------|------|-------------|
| yoloface.onnx | Face Detection | ~6MB | Very Fast |
| arcface_w600k_r50.onnx | Face Recognition | ~92MB | Fast |
| face_landmarker_68.onnx | Facial Landmarks | ~2MB | Fast |
| face_landmarker_68_5.onnx | Landmark Conversion | ~1MB | Very Fast |
| gender_age.onnx | Gender/Age Prediction | ~1MB | Very Fast |

Total model size: ~102MB