#!/usr/bin/env python3
"""
Example V2 API request format for UniversalMediaConverter
Shows the required format for the new v2 system
"""

import json
import requests

def example_webp_request():
    """Example WebP conversion request"""
    
    api_endpoint = "http://localhost:8000/transcode-v2"
    
    # V2 format - each profile MUST have 'config' field with UniversalConverterConfig
    request_data = {
        "media_url": "https://example.com/video.mp4",
        "profiles": [
            {
                "id_profile": "webp_360p",
                "input_type": "video",
                "output_filename": "preview_360p",
                "config": {
                    "output_format": "webp",
                    "width": 360,
                    "height": None,  # Maintain aspect ratio
                    "quality": 85,
                    "fps": 15,
                    "duration": 6.0,
                    "start_time": 0,
                    "speed": 1.0,
                    "lossless": False,
                    "method": 4,
                    "preset": "default",
                    "animated": True,
                    "loop": 0,  # Infinite loop
                    "verbose": True
                }
            },
            {
                "id_profile": "jpg_thumbnail",
                "input_type": "video", 
                "output_filename": "thumbnail",
                "config": {
                    "output_format": "jpg",
                    "width": 300,
                    "height": 300,
                    "jpeg_quality": 90,
                    "optimize": True,
                    "progressive": False
                }
            }
        ],
        "s3_output_config": {
            "bucket": "your-bucket-name",
            "base_path": "transcode-outputs",
            "folder_structure": "{task_id}/profiles/{profile_id}",
            "cleanup_temp_files": True
        },
        "callback_url": "https://your-app.com/webhook/transcode-complete"
    }
    
    # Make request
    response = requests.post(api_endpoint, json=request_data)
    
    print("V2 API Request:")
    print(json.dumps(request_data, indent=2))
    print(f"\nResponse: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
    return response.json()

def example_mp4_request():
    """Example MP4 conversion request"""
    
    api_endpoint = "http://localhost:8000/transcode-v2"
    
    request_data = {
        "media_url": "https://example.com/input-video.avi",
        "profiles": [
            {
                "id_profile": "mp4_1080p",
                "input_type": "video",
                "output_filename": "converted_1080p",
                "config": {
                    "output_format": "mp4",
                    "width": 1920,
                    "height": 1080,
                    "fps": 30,
                    "duration": None,  # Full duration
                    "codec": "h264",
                    "crf": 20,
                    "mp4_preset": "slow",
                    "profile": "high",
                    "level": "4.1",
                    "audio_codec": "aac",
                    "audio_bitrate": "192k",
                    "verbose": True
                }
            }
        ],
        "s3_output_config": {
            "bucket": "media-bucket", 
            "base_path": "videos",
            "cleanup_temp_files": True
        }
    }
    
    response = requests.post(api_endpoint, json=request_data)
    return response.json()

def show_v1_vs_v2_difference():
    """Show the difference between v1 and v2 formats"""
    
    print("=" * 60)
    print("V1 FORMAT (OLD - NO LONGER SUPPORTED):")
    print("=" * 60)
    
    v1_format = {
        "profiles": [
            {
                "id_profile": "webp_360p",
                "output_type": "webp",
                "webp_config": {
                    "width": 360,
                    "quality": 85,
                    "fps": 15,
                    "animated": True
                }
            }
        ]
    }
    
    print(json.dumps(v1_format, indent=2))
    
    print("\n" + "=" * 60)
    print("V2 FORMAT (NEW - REQUIRED):")
    print("=" * 60)
    
    v2_format = {
        "profiles": [
            {
                "id_profile": "webp_360p",
                "input_type": "video",
                "output_filename": "preview_360p",
                "config": {  # THIS IS REQUIRED!
                    "output_format": "webp",  # Explicit format
                    "width": 360,
                    "quality": 85, 
                    "fps": 15,
                    "animated": True,
                    "lossless": False,
                    "method": 4,
                    "loop": 0
                }
            }
        ]
    }
    
    print(json.dumps(v2_format, indent=2))
    
    print("\n" + "=" * 60)
    print("KEY DIFFERENCES:")
    print("=" * 60)
    print("1. V2 requires 'config' field with UniversalConverterConfig format")
    print("2. V2 uses 'output_format' instead of 'output_type'") 
    print("3. V2 has unified parameters for all formats (WebP, JPG, MP4)")
    print("4. V2 supports 'input_type' for better media type filtering")
    print("5. V2 supports 'output_filename' for custom naming")
    print("6. V1 format will be REJECTED by v2 system")

if __name__ == "__main__":
    show_v1_vs_v2_difference()
    print("\nTo test V2 API:")
    print("1. Start the transcode service")
    print("2. Use the example_webp_request() or example_mp4_request() functions")
    print("3. Make sure to use /transcode-v2 endpoint (when implemented)")