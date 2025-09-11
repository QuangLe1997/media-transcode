# PubSub Task Listener

Service để lắng nghe các message từ Google Cloud Pub/Sub và tạo task trong hệ thống transcode, thay thế cho việc gọi API trực tiếp.

## Tính năng

- Lắng nghe messages từ Google Cloud Pub/Sub
- Tạo task tự động từ message với logic tương tự API endpoint `/transcode`
- Hỗ trợ tất cả các tính năng: profile filtering, face detection, callback
- Chỉ hỗ trợ input là URL (không hỗ trợ file upload)
- Tự động retry và error handling
- Logging chi tiết cho monitoring

## Cấu hình

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_BUCKET_NAME=your_bucket
AWS_ENDPOINT_URL=your_endpoint
AWS_ENDPOINT_PUBLIC_URL=your_public_endpoint
AWS_BASE_FOLDER=your_base_folder

# Google Cloud Pub/Sub
PUBSUB_PROJECT_ID=your_project_id
PUBSUB_TASKS_TOPIC=your_tasks_topic
TASKS_SUBSCRIPTION=your_tasks_subscription
PUBSUB_RESULTS_TOPIC=your_results_topic
PUBSUB_RESULTS_SUBSCRIPTION=your_results_subscription
PUBSUB_PUBLISHER_CREDENTIALS_PATH=./key.json
PUBSUB_SUBSCRIBER_CREDENTIALS_PATH=./key.json

# Face Detection
PUBSUB_FACE_DETECTION_TASKS_TOPIC=face-detection-worker-tasks
PUBSUB_FACE_DETECTION_RESULTS_TOPIC=face-detection-worker-results

# Task Listener
PUBSUB_TASK_SUBSCRIPTION=skl-transcode-cms-tasks-sub
```

### Message Format

Message gửi tới PubSub topic phải có format sau:

```json
{
  "task_id": "unique-task-id",
  "media_url": "https://example.com/video.mp4",
  "profiles": [
    {
      "id_profile": "720p",
      "output_type": "video",
      "video_config": {
        "codec": "h264",
        "max_width": 1280,
        "max_height": 720,
        "bitrate": "2M",
        "preset": "fast"
      }
    }
  ],
  "s3_output_config": {
    "base_path": "outputs",
    "folder_structure": "{task_id}/{profile_id}"
  },
  "face_detection_config": {
    "enabled": true,
    "similarity_threshold": 0.6,
    "min_faces_in_group": 2
  },
  "callback_url": "https://your-app.com/callback",
  "callback_auth": {
    "type": "bearer",
    "token": "your-auth-token"
  },
  "pubsub_topic": "your-notification-topic"
}
```

### Required Fields

- `task_id`: Unique identifier cho task
- `media_url`: URL của media file (phải là URL hợp lệ)
- `profiles`: Array các profile transcode
- `s3_output_config`: Cấu hình S3 output

### Optional Fields

- `face_detection_config`: Cấu hình face detection
- `callback_url`: URL để gửi callback khi task hoàn thành
- `callback_auth`: Authentication cho callback
- `pubsub_topic`: Topic để gửi notification

## Chạy Service

### Với Docker Compose

```bash
# Chạy tất cả services
docker-compose up -d

# Chỉ chạy task listener
docker-compose up -d task-listener

# Xem logs
docker-compose logs -f task-listener
```

### Chạy standalone

```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Chạy service
python -m consumer.task_listener
```

## Monitoring

### Logs

Service sẽ log ra:
- Khi nhận được message từ PubSub
- Quá trình tạo task và publish messages
- Các lỗi xảy ra trong quá trình xử lý

### Health Check

Service không expose HTTP endpoint, monitor thông qua:
- Container health status
- Logs
- Database records

## Workflow

1. **Nhận Message**: Listener nhận message từ PubSub subscription
2. **Validate**: Kiểm tra format và required fields
3. **Media Type Detection**: Detect loại media từ URL
4. **Profile Filtering**: Lọc profiles phù hợp với media type
5. **Create Task**: Tạo task record trong database
6. **Publish Messages**: Gửi transcode messages cho từng profile
7. **Face Detection**: Nếu enabled, gửi face detection task
8. **Update Status**: Cập nhật task status thành PROCESSING

## Error Handling

- Message không hợp lệ: nack message để retry
- URL không accessible: skip task và log error
- Database error: retry với exponential backoff
- PubSub publish error: mark profiles as failed

## Khác biệt với API

### Giống nhau:
- Logic tạo task hoàn toàn giống API `/transcode`
- Hỗ trợ tất cả tính năng: profile filtering, face detection, callback
- Cùng database schema và flow

### Khác biệt:
- Chỉ hỗ trợ input URL (không hỗ trợ file upload)
- Nhận input từ PubSub thay vì HTTP request
- Không trả về HTTP response
- Tự động retry failed messages

## Sử dụng

Thay vì gọi API trực tiếp:
```bash
curl -X POST http://api/transcode \
  -F "media_url=https://example.com/video.mp4" \
  -F "profiles=..." \
  -F "s3_output_config=..."
```

Gửi message tới PubSub:
```python
from google.cloud import pubsub_v1
import json

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path('project-id', 'skl-transcode-cms-tasks')

message = {
    "task_id": "unique-id",
    "media_url": "https://example.com/video.mp4",
    "profiles": [...],
    "s3_output_config": {...}
}

future = publisher.publish(
    topic_path,
    json.dumps(message).encode('utf-8')
)
```

## Troubleshooting

### Common Issues

1. **Message không được xử lý**
   - Kiểm tra PubSub credentials
   - Verify topic và subscription tồn tại
   - Check message format

2. **Task tạo thất bại**
   - Kiểm tra database connection
   - Verify media URL accessible
   - Check required fields

3. **Face detection không hoạt động**
   - Verify face detection topic và subscription
   - Check face detection worker đang chạy
   - Review face detection config

### Debug Commands

```bash
# Xem logs chi tiết
docker-compose logs -f task-listener

# Kiểm tra database
docker-compose exec postgres psql -U transcode_user -d transcode_db

# Test PubSub connection
docker-compose exec task-listener python -c "from services.pubsub_service import pubsub_service; print('OK')"
```