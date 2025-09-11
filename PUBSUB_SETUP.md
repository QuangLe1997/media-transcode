# PubSub Configuration Setup

## Quick Fix for Local Development

### Problem
Face detection worker was failing due to missing Google Cloud credentials.

### Solution
1. **Mount Google Cloud credentials**: File `src/transcode_service/key.json` is now properly mounted to `/app/key.json` in all containers
2. **Set environment variables**: Added `GOOGLE_APPLICATION_CREDENTIALS=/app/key.json` to all services
3. **Add disable flag**: Added `DISABLE_PUBSUB` environment variable to disable PubSub completely if needed

### Configuration Options

#### Option 1: Enable PubSub (Recommended)
Set these environment variables in your `.env` file:
```bash
# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=src/transcode_service/key.json

# PubSub Configuration
PUBSUB_PROJECT_ID=your-gcp-project-id
PUBSUB_TASKS_TOPIC=transcode-tasks
TASKS_SUBSCRIPTION=transcode-tasks-sub
PUBSUB_RESULTS_TOPIC=transcode-results
PUBSUB_RESULTS_SUBSCRIPTION=transcode-results-sub
PUBSUB_PUBLISHER_CREDENTIALS_PATH=src/transcode_service/key.json
PUBSUB_SUBSCRIBER_CREDENTIALS_PATH=src/transcode_service/key.json

# Face Detection PubSub (optional)
PUBSUB_FACE_DETECTION_TASKS_TOPIC=face-detection-tasks
PUBSUB_FACE_DETECTION_RESULTS_TOPIC=face-detection-results
FACE_DETECTION_SUBSCRIPTION=face-detection-tasks-sub

# Enable PubSub
DISABLE_PUBSUB=false
```

#### Option 2: Disable PubSub Completely
```bash
DISABLE_PUBSUB=true
```
This will skip PubSub initialization and prevent errors if you don't have Google Cloud credentials.

### Files Modified
- `docker-compose.local.yml`: Added proper credentials mounting and environment variables
- `docker-compose.yml`: Added `GOOGLE_APPLICATION_CREDENTIALS` and `DISABLE_PUBSUB` support
- `src/transcode_service/services/pubsub_service.py`: Added graceful handling for disabled PubSub
- `src/transcode_service/core/config.py`: Added `disable_pubsub` and `google_application_credentials` settings

### Testing
```bash
# Clean and rebuild
docker system prune -a -f
./build-local.sh build

# Start services
./build-local.sh up

# Check logs
./build-local.sh logs
```

### Notes
- The `key.json` file must exist in `src/transcode_service/` directory
- If PubSub is disabled, workers will skip message listening but still function for direct API calls
- All Docker Compose files now use consistent credential paths