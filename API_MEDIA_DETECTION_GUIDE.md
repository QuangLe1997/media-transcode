# API Media Detection & Profile Filtering Guide

## Overview

The transcode API now automatically detects input media type and filters profiles to only run those appropriate for the detected media type.

## New Features

### 1. Automatic Media Type Detection
- **File uploads**: Uses filename extension and MIME content type
- **URL inputs**: Uses URL path extension and MIME type guessing
- **Supported types**: `image` and `video`

### 2. Profile Filtering
- Profiles with `input_type: "image"` only run for image inputs
- Profiles with `input_type: "video"` only run for video inputs  
- Profiles without `input_type` run for all inputs (backward compatibility)

### 3. Enhanced API Response
- Returns media detection summary
- Shows original vs filtered profile counts
- Lists skipped profiles for debugging

## API Changes

### Request Format (unchanged)
```bash
curl -X POST "http://localhost:8000/transcode" \
  -F "media_url=https://example.com/sample.mp4" \
  -F "profiles='[...]'" \
  -F "s3_output_config='[...]'"
```

### Response Format (enhanced)
```json
{
  "task_id": "12345678-1234-1234-1234-123456789012",
  "status": "processing",
  "source_url": "https://example.com/sample.mp4",
  "input_type": "url",
  "profiles_count": 3,
  "media_detection": {
    "detected_media_type": "video",
    "original_profiles_count": 5,
    "filtered_profiles_count": 3,
    "skipped_profiles_count": 2,
    "skipped_profiles": ["high_main_image", "high_thumbs_image_s"]
  }
}
```

## Profile Configuration

### Adding input_type to profiles
```json
{
  "id_profile": "high_main_image",
  "output_type": "image",
  "input_type": "image",
  "image_config": {
    "max_width": 1080,
    "max_height": 1440,
    "quality": 90,
    "format": "jpeg"
  }
}
```

### Faceswap Profile Examples

#### Image Input Profiles
```json
[
  {
    "id_profile": "high_main_image",
    "output_type": "image",
    "input_type": "image",
    "image_config": {
      "max_width": 1080,
      "max_height": 1440,
      "quality": 90,
      "format": "jpeg",
      "thumbnail_mode": false
    }
  },
  {
    "id_profile": "high_thumbs_image_s",
    "output_type": "image", 
    "input_type": "image",
    "image_config": {
      "max_width": 240,
      "max_height": 320,
      "quality": 75,
      "format": "jpeg",
      "thumbnail_mode": true
    }
  }
]
```

#### Video Input Profiles
```json
[
  {
    "id_profile": "high_main_video",
    "output_type": "video",
    "input_type": "video",
    "video_config": {
      "codec": "libx264",
      "max_width": 1080,
      "max_height": 1440,
      "crf": 20,
      "max_bitrate": "4M",
      "preset": "medium",
      "profile": "high",
      "level": "4.1",
      "max_fps": 30,
      "audio_codec": "aac",
      "audio_bitrate": "128k"
    }
  },
  {
    "id_profile": "high_video_thumbs_image_s",
    "output_type": "image",
    "input_type": "video",
    "image_config": {
      "max_width": 240,
      "max_height": 320,
      "quality": 75,
      "format": "jpeg",
      "thumbnail_mode": true,
      "extract_time": 1.0
    }
  }
]
```

## Media Type Detection Logic

### Detection Priority
1. **MIME Content Type** (most reliable)
2. **File Extension** (filename or URL path)
3. **MIME Guessing** (from URL)
4. **Default to Video** (if unable to determine)

### Supported File Types

#### Video Extensions
- `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, `.m4v`, `.3gp`, `.flv`, `.wmv`, `.mpg`, `.mpeg`

#### Image Extensions  
- `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.tiff`, `.tif`, `.svg`

#### Video MIME Types
- `video/mp4`, `video/avi`, `video/quicktime`, `video/x-msvideo`, `video/webm`, `video/x-matroska`, `video/3gpp`, `video/x-flv`

#### Image MIME Types
- `image/jpeg`, `image/png`, `image/gif`, `image/bmp`, `image/webp`, `image/tiff`, `image/svg+xml`

## Workflow Examples

### Image Input Workflow
```
Input: photo.jpg (image/jpeg)
↓
Detect: media_type = "image"
↓
Filter: Only profiles with input_type = "image" or null
↓
Run: high_main_image, high_thumbs_image_s, high_thumbs_image_m, high_thumbs_image_l
Skip: All video profiles
```

### Video Input Workflow
```
Input: movie.mp4 (video/mp4)
↓
Detect: media_type = "video"  
↓
Filter: Only profiles with input_type = "video" or null
↓
Run: high_main_video, high_thumbs_video_s, high_thumbs_gif_s, high_video_thumbs_image_s
Skip: All image-only profiles
```

## Error Handling

### No Matching Profiles
```json
{
  "detail": "No profiles match the detected media type 'image'. Skipped profiles: ['high_main_video', 'high_thumbs_video_s']"
}
```

### Invalid Input Type
- API automatically detects type, no manual specification needed
- Unsupported files default to video processing

## Backward Compatibility

- Profiles without `input_type` field run for all inputs
- Existing API calls continue to work unchanged
- New `media_detection` field added to response (optional)

## Implementation Notes

### Media Detection Service
- Located in `services/media_detection_service.py`
- Provides `detect_media_type()` and `filter_profiles_by_input_type()` methods
- Handles edge cases and fallback logic

### Schema Updates
- `TranscodeProfile` now includes optional `input_type` field
- Validates `input_type` as `"image"` or `"video"`
- Maintains backward compatibility

### Logging
- Logs media type detection decisions
- Logs profile filtering results
- Provides detailed filtering summary

## Testing

Use the provided test files:
- `test_media_detection.py` - Test detection logic
- `test_api_example.py` - Show expected API behavior
- `faceswap_profiles_config.json` - Complete profile configuration

## Migration Guide

### For Existing Configs
1. Add `input_type` field to all profiles
2. Set `"input_type": "image"` for image processing profiles
3. Set `"input_type": "video"` for video processing profiles
4. Leave `input_type` null for universal profiles

### For API Consumers
1. API calls remain unchanged
2. Check new `media_detection` field in response
3. Handle potential profile filtering (fewer profiles may run)
4. Use skipped profiles info for debugging

## Benefits

✅ **Automatic optimization** - Only relevant profiles run
✅ **Better performance** - Fewer unnecessary transcoding tasks
✅ **Clear feedback** - Know exactly which profiles ran/skipped
✅ **Backward compatible** - Existing configs continue working
✅ **Flexible** - Easy to add new media types in future