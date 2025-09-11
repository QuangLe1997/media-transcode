# 📋 Config Profiles Documentation - Media Transcode System

## 🎯 Tổng quan

Config Profiles là hệ thống cấu hình mạnh mẽ cho phép người dùng định nghĩa các quy trình xử lý media phức tạp thông qua JSON. Mỗi profile bao gồm nhiều settings cho video processing, image processing, face detection và output management.

## 🏗️ Cấu trúc Database

### Config Model
```sql
CREATE TABLE configs (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    config_json TEXT NOT NULL,        -- JSON configuration
    user_id INTEGER REFERENCES users(id),
    is_default BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Relationships
```
User (1) → (N) Config
Config (1) → (N) Job
Job (1) → (N) Media → (N) TranscodeTask → (N) TranscodeOutput
```

## 📋 Cấu trúc JSON Config

### Schema Overview
```json
{
  "config_name": "string",
  "description": "string", 
  "created_at": "ISO datetime",
  "video_settings": { ... },
  "image_settings": { ... },
  "face_detection": { ... },
  "output_settings": { ... },
  "quality_settings": { ... },
  "performance_settings": { ... }
}
```

## 🎥 Video Settings

### 1. Video Transcode Profiles
```json
"video_settings": {
  "transcode_profiles": [
    {
      "name": "720p_medium",
      "width": 1280,
      "height": 720,
      "codec": "libx264",                    // libx264, libx265, libvpx-vp9
      "preset": "medium",                    // ultrafast, fast, medium, slow, veryslow
      "crf": 23,                            // Quality: 18-28 (lower = better)
      "format": "mp4",                      // mp4, webm, mkv
      "audio_codec": "aac",                 // aac, libopus, mp3
      "audio_bitrate": "128k",              // 96k, 128k, 192k, 256k, 320k
      "use_gpu": true,                      // Enable hardware acceleration
      "start": 30,                          // Start time (seconds) - optional
      "end": 90,                           // End time (seconds) - optional
      "gpu_options": {                      // Hardware acceleration settings
        "hardware_encoder": "h264_nvenc",   // h264_nvenc, h264_amf, h264_qsv, h264_videotoolbox
        "preset": "p4",                     // NVENC: p1-p7, AMF: speed, QSV: medium
        "rc": "vbr"                         // Rate control: vbr, cbr, cqp
      }
    }
  ]
}
```

#### Codec Options
| Codec | Description | Use Case | Hardware Support |
|-------|-------------|----------|------------------|
| `libx264` | H.264 software | Universal compatibility | CPU only |
| `h264_nvenc` | H.264 NVIDIA | Fast encoding with NVIDIA GPUs | NVIDIA |
| `h264_amf` | H.264 AMD | AMD GPU acceleration | AMD |
| `h264_qsv` | H.264 Intel | Intel GPU acceleration | Intel |
| `h264_videotoolbox` | H.264 Apple | macOS hardware acceleration | Apple Silicon/Intel Mac |
| `libx265` | H.265/HEVC software | High compression | CPU only |
| `hevc_nvenc` | H.265 NVIDIA | NVIDIA GPU HEVC | NVIDIA |
| `libvpx-vp9` | VP9 | Web streaming | CPU only |

#### Preset Mapping
- **ultrafast**: Fastest encoding, larger files
- **fast**: Good speed/quality balance
- **medium**: Default balance
- **slow**: Better quality, slower encoding
- **veryslow**: Best quality, slowest encoding

#### CRF Quality Guidelines
- **18**: Visually lossless
- **23**: Default (good quality)
- **28**: Lower quality, smaller files
- **Higher values**: Lower quality

### 2. Video Preview Settings (GIF Creation)
```json
"preview_settings": {
  "profiles": [
    {
      "name": "small_gif",
      "start": 0,                          // Start time (seconds)
      "end": 5,                           // Duration (seconds)
      "fps": 10,                          // Frame rate (1-30)
      "width": 320,                       // Output width
      "height": 180,                      // Output height  
      "quality": 80,                      // Quality (1-100)
      "format": "gif",                    // gif, webm, mp4
      "loop": true                        // Loop animation - optional
    }
  ]
}
```

#### GIF Quality Guidelines
- **70-75**: Small file size, acceptable quality
- **80-85**: Good balance
- **90-95**: High quality, larger files

### 3. Video Thumbnail Settings
```json
"thumbnail_settings": {
  "timestamp": 5,                        // Time to extract (seconds)
  "profiles": [
    {
      "name": "medium",
      "width": 640,
      "height": 360,
      "format": "jpg",                   // jpg, png, webp
      "quality": 90                      // Quality (1-100)
    }
  ]
}
```

#### Multi-Thumbnail Support
```json
"multi_thumbnail_settings": {
  "timestamps": [1, 5, 10, 15, 20],     // Multiple time points
  "profile": {
    "name": "timeline_thumbs",
    "width": 320,
    "height": 180,
    "format": "jpg",
    "quality": 85
  }
}
```

## 🖼️ Image Settings

### 1. Image Transcode Profiles
```json
"image_settings": {
  "transcode_profiles": [
    {
      "name": "optimized_webp",
      "format": "webp",                   // webp, jpg, png, avif
      "quality": 90,                     // Quality (1-100)
      "resize": true,                    // Enable resizing
      "width": 1920,                     // Target width
      "height": 1080,                    // Target height
      "maintain_aspect_ratio": true,     // Preserve aspect ratio
      "compression_level": 6             // PNG compression (0-9)
    }
  ]
}
```

#### Format Comparison
| Format | Best Use Case | Quality | File Size | Browser Support |
|--------|---------------|---------|-----------|-----------------|
| `webp` | Web optimization | Excellent | Small | Modern browsers |
| `jpg` | Photos, universal | Good | Medium | Universal |
| `png` | Graphics, transparency | Excellent | Large | Universal |
| `avif` | Next-gen web | Excellent | Very Small | Limited |

### 2. Image Thumbnail Profiles
```json
"thumbnail_profiles": [
  {
    "name": "social_media",
    "width": 1200,
    "height": 630,
    "maintain_aspect_ratio": false,      // Crop to exact dimensions
    "format": "jpg",
    "quality": 85
  },
  {
    "name": "responsive_small",
    "width": 320,
    "height": 240,
    "maintain_aspect_ratio": true,       // Keep original ratio
    "format": "webp",
    "quality": 85
  }
]
```

## 👤 Face Detection Configuration

### Core Configuration
```json
"face_detection": {
  "enabled": true,
  "config": {
    // Detection Parameters
    "face_detector_size": "640x640",           // Model input size: 320x320, 640x640
    "face_detector_score_threshold": 0.8,     // Detection confidence (0.0-1.0)
    "min_appearance_ratio": 0.05,             // Min face size ratio to frame
    "min_frontality": 0.1,                    // Min frontal face angle (0.0-1.0)
    
    // Sampling & Processing
    "sample_interval": 1,                     // Process every N frames
    "ignore_frames": [0, 1, 2],              // Skip specific frames
    "ignore_ranges": [[100, 200], [500, 600]], // Skip time ranges (seconds)
    "max_workers": 6,                         // Parallel processing threads
    
    // Recognition & Clustering
    "similarity_threshold": 0.7,              // Face similarity (0.0-1.0)
    "min_faces_in_group": 1,                 // Min faces per person cluster
    
    // Avatar Generation
    "avatar_size": 512,                       // Avatar dimensions (pixels)
    "avatar_padding": 0.2,                    // Padding around face (0.0-1.0)
    "avatar_quality": 95,                     // Avatar image quality (1-100)
    
    // Output Settings
    "output_path": "./output/faces/",         // Local output directory
    
    // Advanced Analysis
    "detailed_analysis": {
      "age_estimation": true,                 // Estimate age
      "gender_classification": true,          // Classify gender  
      "emotion_detection": true,              // Detect emotions
      "facial_landmarks": true,               // Extract facial landmarks
      "face_quality_score": true             // Assess face quality
    },
    
    // Clustering Options
    "clustering_options": {
      "algorithm": "dbscan",                  // dbscan, kmeans
      "eps": 0.35,                           // DBSCAN epsilon parameter
      "min_samples": 2,                      // DBSCAN min samples
      "enable_hierarchical": true            // Multi-level clustering
    },
    
    // Output Formats
    "output_formats": {
      "save_json_metadata": true,            // Save detection metadata
      "save_csv_summary": true,              // Export CSV summary
      "save_face_gallery": true,             // Generate HTML gallery
      "gallery_format": "html"               // html, json
    }
  }
}
```

### Face Detection Parameters Guide

#### Detection Thresholds
- **face_detector_score_threshold**: 0.5-0.9 (higher = more strict)
- **min_appearance_ratio**: 0.05-0.2 (min face size in frame)
- **min_frontality**: 0.1-0.5 (frontal face requirement)

#### Clustering Parameters
- **similarity_threshold**: 0.6-0.8 (face similarity for grouping)
- **eps**: 0.3-0.5 (DBSCAN cluster distance)
- **min_samples**: 1-5 (min faces per person)

#### Performance Tuning
- **sample_interval**: 1-10 (process every N frames)
- **max_workers**: 2-8 (parallel threads)

## ⚙️ Output Settings

### Storage Configuration
```json
"output_settings": {
  "s3_bucket": "media-transcode-bucket",
  "folder_structure": "{user_id}/{job_id}/{type}/{profile_name}/",
  "generate_unique_filenames": true,        // UUID prefixes
  "preserve_original_filename": true,       // Keep original names
  "use_temporary_local_storage": true,      // Local processing
  "local_storage_path": "/tmp/transcode-jobs/",
  "delete_local_after_upload": true,       // Cleanup after upload
  "create_manifest": true,                 // Generate file manifest
  "manifest_format": "json"                // json, xml
}
```

#### Folder Structure Variables
- `{user_id}`: User ID number
- `{job_id}`: Job ID number  
- `{type}`: video, image, thumbnail, preview, faces
- `{profile_name}`: Profile name from config
- `{timestamp}`: Current timestamp
- `{media_id}`: Media file ID

## 🎛️ Quality & Performance Settings

### Quality Analysis
```json
"quality_settings": {
  "enable_quality_analysis": true,
  "video_quality_metrics": ["psnr", "ssim", "vmaf"],
  "image_quality_metrics": ["psnr", "ssim"],
  "save_quality_reports": true
}
```

### Performance Tuning
```json
"performance_settings": {
  "max_concurrent_tasks": 4,               // Parallel task limit
  "timeout_seconds": 1800,                // Task timeout (30 min)
  "retry_attempts": 2,                    // Failed task retries
  "progress_reporting_interval": 5        // Progress update frequency
}
```

## 📋 Config Template Examples

### 1. Standard Profile
**Use Case**: General-purpose transcoding
```json
{
  "config_name": "Standard Transcode Profile",
  "video_settings": {
    "transcode_profiles": [
      {"name": "480p", "width": 854, "height": 480, "crf": 23},
      {"name": "720p", "width": 1280, "height": 720, "crf": 23},
      {"name": "1080p", "width": 1920, "height": 1080, "crf": 23}
    ],
    "preview_settings": {
      "profiles": [
        {"name": "small_gif", "width": 320, "fps": 10, "quality": 80}
      ]
    }
  },
  "face_detection": {"enabled": true}
}
```

### 2. High-Quality Profile  
**Use Case**: Professional content creation
```json
{
  "config_name": "High-Quality Configuration",
  "video_settings": {
    "transcode_profiles": [
      {"name": "1080p", "crf": 17, "preset": "slow"},
      {"name": "1440p", "width": 2560, "height": 1440, "crf": 16},
      {"name": "2160p", "width": 3840, "height": 2160, "crf": 15}
    ]
  }
}
```

### 3. Minimal Profile
**Use Case**: Quick processing, low resource usage
```json
{
  "config_name": "Minimal Configuration", 
  "video_settings": {
    "transcode_profiles": [
      {"name": "720p", "preset": "fast", "crf": 25}
    ]
  },
  "face_detection": {"enabled": false}
}
```

### 4. GIF Maker Profile
**Use Case**: Specialized GIF creation
```json
{
  "config_name": "GIF Maker Configuration",
  "video_settings": {
    "preview_settings": {
      "profiles": [
        {"name": "tiny_gif", "width": 240, "fps": 8, "quality": 70},
        {"name": "hq_gif", "width": 800, "fps": 20, "quality": 90}
      ]
    }
  }
}
```

### 5. Face Detection Focus
**Use Case**: Advanced face analysis
```json
{
  "config_name": "Face Detection Focus Configuration",
  "face_detection": {
    "enabled": true,
    "config": {
      "face_detector_score_threshold": 0.8,
      "detailed_analysis": {
        "age_estimation": true,
        "gender_classification": true,
        "emotion_detection": true
      }
    }
  }
}
```

## 🔄 Config Processing Flow

### 1. Config Loading
```python
# TranscodeService.get_job_config()
config = json.loads(config.config_json)
```

### 2. Task Creation
```python
# For each media file, create tasks based on config
for profile in config['video_settings']['transcode_profiles']:
    task = TranscodeTask(
        media_id=media.id,
        task_type='transcode', 
        profile_name=profile['name']
    )
```

### 3. Parameter Mapping
```python
# Map config to FFmpeg parameters
ffmpeg_service.transcode_video(
    width=profile['width'],
    height=profile['height'], 
    codec=profile['codec'],
    crf=profile['crf']
)
```

## ⚡ Hardware Acceleration

### Auto-Detection Logic
```python
# System detects best available encoder
if nvidia_gpu:
    return "h264_nvenc"
elif amd_gpu:
    return "h264_amf"  
elif intel_gpu:
    return "h264_qsv"
elif macos:
    return "h264_videotoolbox"
else:
    return "libx264"  # Software fallback
```

### GPU Options Configuration
```json
"gpu_options": {
  "hardware_encoder": "h264_nvenc",
  "preset": "p4",                    // NVENC: p1-p7 (p1=slow, p7=fast)
  "rc": "vbr",                      // Rate control: vbr, cbr, cqp
  "profile": "high",                // H.264 profile
  "level": "4.1",                   // H.264 level
  "b_frames": 3,                    // B-frame count
  "refs": 3                         // Reference frames
}
```

## 🛠️ Configuration Management

### Creating New Configs
```python
# Via API
POST /api/configs
{
  "name": "My Custom Config",
  "description": "Custom processing setup",
  "config_json": "{...}"
}
```

### Config Validation
```python
def validate_config(config_json):
    required_sections = ['video_settings', 'image_settings']
    config = json.loads(config_json)
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing {section}")
```

### Default Configs
```python
# System provides default templates
default_configs = [
    "standard.json",
    "minimal.json", 
    "high-quality.json",
    "comprehensive-test.json"
]
```

## 🔍 Troubleshooting

### Common Issues

1. **Invalid JSON Syntax**
   ```
   Error: Invalid JSON in config 123
   Solution: Validate JSON syntax
   ```

2. **Missing Required Fields**
   ```
   Error: Missing video_settings.transcode_profiles
   Solution: Add required profile sections
   ```

3. **Hardware Acceleration Failures**
   ```
   Error: NVENC encoder not available
   Solution: Falls back to software encoding
   ```

4. **Face Detection Model Loading**
   ```
   Error: ONNX model not found
   Solution: System uses mock face processor
   ```

### Performance Optimization

1. **Reduce CRF values** for better quality (slower)
2. **Increase sample_interval** for face detection (faster)
3. **Limit max_concurrent_tasks** to prevent overload
4. **Use hardware acceleration** when available
5. **Optimize frame rates** for GIF generation

## 📚 Best Practices

### 1. Config Design
- **Start with templates** and customize
- **Test with small files** first
- **Use meaningful profile names**
- **Document custom settings**

### 2. Performance
- **Balance quality vs. speed** with CRF/preset
- **Use appropriate resolutions** for target devices
- **Enable hardware acceleration** when available
- **Limit concurrent processing** based on system resources

### 3. Storage
- **Configure S3 buckets** for production
- **Use folder structures** for organization  
- **Enable cleanup** to manage disk space
- **Generate manifests** for tracking outputs

### 4. Face Detection
- **Tune thresholds** for your content type
- **Sample appropriately** for video length
- **Use clustering** for person identification
- **Configure output formats** for downstream use

This documentation provides comprehensive guidance for creating and managing configuration profiles in the Media Transcode System. Each config profile enables sophisticated media processing workflows tailored to specific requirements and use cases.