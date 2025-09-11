# Face Detection Consumer

Face Detection Consumer tự động kiểm tra và tải xuống các model khi khởi động, cung cấp khả năng phát hiện khuôn mặt, nhận diện, và phân tích trong video/hình ảnh.

## ✨ Tính năng

- **🤖 Auto Model Download**: Tự động tải xuống và validate models khi khởi động
- **🔍 Face Detection**: Phát hiện khuôn mặt với YOLOFace 
- **👥 Face Recognition**: Nhận diện và clustering khuôn mặt với ArcFace
- **📊 Demographics**: Phân tích giới tính và tuổi
- **⚡ GPU Support**: Hỗ trợ CUDA để tăng tốc
- **🏥 Health Check**: Kiểm tra trạng thái models và dependencies
- **🔄 Parallel Processing**: Xử lý đa luồng cho video

## 🎯 Models được sử dụng

Consumer sẽ tự động tải xuống các models sau:

1. **YOLOFace** (`yoloface.onnx`) - Face detection
2. **ArcFace** (`arcface_w600k_r50.onnx`) - Face recognition  
3. **Face Landmarker 68** (`face_landmarker_68.onnx`) - 68-point landmarks
4. **Face Landmarker 68/5** (`face_landmarker_68_5.onnx`) - 5-point landmarks
5. **Gender/Age** (`gender_age.onnx`) - Demographics analysis

## 🚀 Cách sử dụng

### 1. Chạy test để kiểm tra

```bash
python scripts/test_face_detection.py
```

### 2. Chạy Face Detection Worker

```bash
python scripts/run_face_detection_worker.py
```

### 3. Chạy qua Docker

```bash
# Với face detection support
docker-compose -f docker-compose.yml up face-detection-worker

# Hoặc với GPU support
docker-compose -f docker-compose.gpu.yml up face-detection-worker
```

## 📝 Cấu hình

Consumer có thể được cấu hình thông qua các tham số:

```python
config = {
    # Face detection
    "face_detector_size": "640x640",
    "face_detector_score_threshold": 0.5,
    "face_landmarker_score_threshold": 0.85,
    "iou_threshold": 0.4,
    
    # Face clustering
    "similarity_threshold": 0.6,
    "min_faces_in_group": 3,
    "min_appearance_ratio": 0.25,
    "min_frontality": 0.2,
    
    # Video processing
    "sample_interval": 5,
    "start_frame": 0,
    "end_frame": None,
    "ignore_frames": [],
    "ignore_ranges": [],
    
    # Output
    "avatar_size": 112,
    "avatar_padding": 0.07,
    "avatar_quality": 85,
    "save_faces": True,
    
    # Performance
    "max_workers": 4
}
```

## 📊 Message Format

### Input Message (FaceDetectionMessage)
```json
{
    "task_id": "unique_task_id",
    "source_url": "s3://bucket/video.mp4",
    "config": {
        "similarity_threshold": 0.6,
        "min_faces_in_group": 3,
        "save_faces": true
    }
}
```

### Output Message (FaceDetectionResult)
```json
{
    "task_id": "unique_task_id",
    "status": "completed",
    "faces": [
        {
            "name": "000150_00",
            "group_size": 25,
            "index": 0,
            "avatar": "base64_encoded_image",
            "bounding_box": [x1, y1, x2, y2],
            "detector": 0.95,
            "landmarker": 0.87,
            "normed_embedding": [...],
            "gender": 1,
            "age": 25,
            "metrics": {
                "mean_distance": 0.15,
                "pose_avg_frontality": 0.85
            }
        }
    ],
    "is_change_index": false,
    "output_urls": ["s3://bucket/faces/face_00.jpg"],
    "completed_at": "2024-01-01T12:00:00Z"
}
```

## 🏥 Health Check

Consumer cung cấp health check API:

```python
worker = FaceDetectionWorker()
health_status = worker.health_check()

# Trả về:
{
    "status": "healthy|degraded|unhealthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "models": {
        "yoloface.onnx": {
            "available": true,
            "valid": true,
            "path": "/path/to/model"
        }
    },
    "dependencies": {
        "opencv": {"available": true, "version": "4.8.0"},
        "onnxruntime": {"available": true, "version": "1.16.0"}
    }
}
```

## 🔧 Troubleshooting

### Models không tải được
- Kiểm tra kết nối internet
- Thử force download: `downloader.download_all_models(force_download=True)`
- Xem logs để biết lỗi cụ thể

### Performance chậm
- Sử dụng GPU: Cài đặt `onnxruntime-gpu`
- Giảm `face_detector_size` xuống "320x320"
- Tăng `sample_interval` để process ít frame hơn
- Giảm `max_workers` nếu RAM hạn chế

### Memory issues
- Giảm `max_workers`
- Tăng `sample_interval`
- Sử dụng `ignore_ranges` để skip một số phần video

## 📈 Monitoring

Consumer ghi logs chi tiết:
- Model download progress
- Face detection results  
- Performance metrics
- Error handling

Logs được lưu tại `logs/face_detect_consumer.log`

## 🚀 Deployment

### Development
```bash
python scripts/run_face_detection_worker.py
```

### Production with Docker
```bash
docker-compose up -d face-detection-worker
```

### With GPU support
```bash
docker-compose -f docker-compose.gpu.yml up -d face-detection-worker
```

## 🔒 Security

- Models được validate checksum khi download
- Chỉ process trusted input sources
- Sandbox execution trong Docker container
- Automatic cleanup của temp files

## 📋 Requirements

- Python 3.8+
- OpenCV 4.0+
- ONNX Runtime 1.12+
- NumPy, scikit-learn
- Google Cloud Pub/Sub
- AWS S3 (for storage)

Tất cả dependencies được tự động cài đặt khi chạy `pip install -r requirements-face-detection.txt`